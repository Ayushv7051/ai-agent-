"""
Agent Orchestration Engine for Ayush AI.
Coordinates the reasoning-action-observation loop with live progress callbacks,
interactive approvals, task tracking, and loop limit enforcement.
"""

import json
from typing import Dict, Any, List, Optional, Callable
from config import MAX_AGENT_ITERATIONS, TOOL_TIMEOUT_SECONDS
from agent.brain import ask_model, check_ollama
from agent.tools import get_available_tools_schema, select_relevant_tools, execute_tool, REGISTRY
from agent.task_manager import task_manager
from agent.task_state import TaskStatus
from agent.permissions import (
    get_pending_approval,
    approve_action,
    reject_action,
    PendingApproval
)
from agent.schemas import ToolActivity, ChatResponse, PendingApproval as PendingApprovalSchema
from agent.logger import logger


class AgentOrchestrator:
    """Coordinates conversation, multi-step tool execution, and approval lifecycles."""

    def __init__(self, max_iterations: int = MAX_AGENT_ITERATIONS):
        self.max_iterations = max_iterations

    def run(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
        approval_callback: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> ChatResponse:
        """
        Executes an agent reasoning-action cycle for a user message.
        Iterates up to max_iterations (default 8) while tool calls are made.
        """
        logger.info(f"Agent Orchestrator handling message: '{user_message}'")
        
        # 1. Register Task in TaskManager
        task = task_manager.create_task(user_request=user_message, max_steps=self.max_iterations)

        # 2. Check Ollama Status First
        online, status_msg, _ = check_ollama()
        if not online:
            task_manager.set_status(task.task_id, TaskStatus.FAILED, error=status_msg)
            return ChatResponse(
                response=status_msg,
                tool_activities=[
                    ToolActivity(
                        tool="ollama",
                        action="check_connection",
                        status="error",
                        details="Cannot connect to Ollama. Please start Ollama and try again."
                    )
                ]
            )

        tool_activities: List[ToolActivity] = []
        messages: List[Dict[str, Any]] = []

        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        tools_schema = select_relevant_tools(user_message)
        iteration_count = 0
        final_answer = ""
        pending_approval_obj: Optional[PendingApprovalSchema] = None

        if progress_callback:
            progress_callback(1, self.max_iterations, "understanding", "Analyzing request and planning actions...")

        while iteration_count < self.max_iterations:
            iteration_count += 1
            task_manager.update_step(task.task_id, iteration_count)
            logger.info(f"Agent reasoning turn {iteration_count}/{self.max_iterations}")

            # AI decides next step
            step_result = ask_model(messages=messages, tools=tools_schema)
            assistant_content = step_result.get("content", "")
            tool_calls = step_result.get("tool_calls", [])

            # Case A: No tools required; AI completed thought or answered directly
            if not tool_calls:
                final_answer = assistant_content
                break

            # Append assistant message to context
            messages.append({
                "role": "assistant",
                "content": assistant_content or "Calling requested tool(s)..."
            })

            # Case B: Tool(s) invoked
            for tc in tool_calls:
                tool_name = tc.tool
                tool_args = tc.arguments
                task_manager.update_step(task.task_id, iteration_count, tool_name)

                action_desc = f"Executing {tool_name}..."
                if progress_callback:
                    progress_callback(iteration_count, self.max_iterations, tool_name, f"Using tool '{tool_name}'...")

                logger.info(f"Orchestrator executing tool: '{tool_name}' (Turn {iteration_count})")
                
                tool_activities.append(ToolActivity(
                    tool=tool_name,
                    action="invoke",
                    status="running",
                    details=f"Parameters: {json.dumps(tool_args)}"
                ))

                # Execute with validation, permission, and timeout checks
                exec_output = execute_tool(
                    tool_name=tool_name,
                    arguments=tool_args,
                    timeout_seconds=TOOL_TIMEOUT_SECONDS,
                    approval_callback=approval_callback
                )

                # Check if action was intercepted for asynchronous web approval
                if exec_output.get("status") == "pending_approval":
                    appr_data = exec_output.get("pending_approval")
                    pending_approval_obj = PendingApprovalSchema(**appr_data)
                    task_manager.set_status(task.task_id, TaskStatus.WAITING_FOR_APPROVAL)
                    
                    tool_activities.append(ToolActivity(
                        tool=tool_name,
                        action="approval_required",
                        status="pending_approval",
                        details=f"Action paused. Waiting for human approval [ID: {pending_approval_obj.id}]"
                    ))
                    
                    return ChatResponse(
                        response=f"Action '{tool_name}' requires your explicit approval before proceeding.\n\n"
                                 f"Reason: {pending_approval_obj.reason}\n"
                                 f"Parameters: {json.dumps(tool_args, indent=2)}",
                        tool_activities=tool_activities,
                        pending_approval=pending_approval_obj
                    )

                # Tool completed or failed
                is_success = exec_output.get("success", False)
                res_val = exec_output.get("result")
                verif = exec_output.get("verification", {})
                
                details_str = verif.get("details") or (res_val.get("message") if isinstance(res_val, dict) else str(res_val)[:150])

                if is_success:
                    tool_activities.append(ToolActivity(
                        tool=tool_name,
                        action="completed",
                        status="success",
                        details=details_str
                    ))
                    if progress_callback:
                        progress_callback(iteration_count, self.max_iterations, tool_name, f"✓ {details_str}")
                    
                    # Supply verified tool result back to model
                    tool_msg_content = json.dumps(res_val, default=str)
                    messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": tool_msg_content
                    })
                else:
                    err_msg = exec_output.get("error", "Tool execution failed")
                    tool_activities.append(ToolActivity(
                        tool=tool_name,
                        action="failed",
                        status="error",
                        details=err_msg
                    ))
                    if progress_callback:
                        progress_callback(iteration_count, self.max_iterations, tool_name, f"✗ Failed: {err_msg}")

                    messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps({"error": err_msg})
                    })

        # Loop limit reached guard
        if iteration_count >= self.max_iterations and not final_answer:
            logger.warning(f"Agent reached maximum iteration limit ({self.max_iterations})")
            if progress_callback:
                progress_callback(self.max_iterations, self.max_iterations, "cap", "Task stopped safely because maximum iteration limit was reached.")
            
            tool_activities.append(ToolActivity(
                tool="orchestrator",
                action="iteration_cap",
                status="skipped",
                details=f"Reached maximum tool loop limit of {self.max_iterations} iterations."
            ))
            messages.append({
                "role": "user",
                "content": "Please synthesize and summarize all results gathered so far concisely."
            })
            synthesis = ask_model(messages=messages, tools=None)
            final_answer = synthesis.get("content", "Completed all permitted tool iterations.")

        task_manager.set_status(task.task_id, TaskStatus.COMPLETED, summary=final_answer[:200])
        return ChatResponse(
            response=final_answer or "Task completed.",
            tool_activities=tool_activities,
            pending_approval=pending_approval_obj
        )

    def execute_approved_action(self, approval_id: str) -> ChatResponse:
        """Executes a previously pending action once the user grants approval."""
        success, approval = approve_action(approval_id)
        if not success or not approval:
            return ChatResponse(
                response=f"Unable to approve request with ID '{approval_id}'. It may not exist or is already resolved.",
                tool_activities=[
                    ToolActivity(
                        tool="permissions",
                        action="approve",
                        status="error",
                        details="Invalid or expired approval ID"
                    )
                ]
            )

        tool_def = REGISTRY.get(approval.tool)
        if not tool_def:
            return ChatResponse(
                response=f"Tool '{approval.tool}' is no longer registered."
            )

        try:
            validated_args = tool_def.schema(**approval.arguments).model_dump()
            result = tool_def.handler(validated_args)
            return ChatResponse(
                response=f"Successfully executed approved action '{approval.tool}'.\nResult: {json.dumps(result, indent=2, default=str)}",
                tool_activities=[
                    ToolActivity(
                        tool=approval.tool,
                        action="completed",
                        status="success",
                        details=f"Action executed: {str(result)[:200]}"
                    )
                ]
            )
        except Exception as e:
            return ChatResponse(
                response=f"Error executing approved action '{approval.tool}': {str(e)}"
            )

    def reject_pending_action(self, approval_id: str) -> ChatResponse:
        """Rejects a pending approval request."""
        success, approval = reject_action(approval_id)
        if not success or not approval:
            return ChatResponse(
                response=f"Approval request '{approval_id}' not found or already closed."
            )

        return ChatResponse(
            response=f"Action '{approval.tool}' has been rejected by the user. No changes were made.",
            tool_activities=[
                ToolActivity(
                    tool=approval.tool,
                    action="reject",
                    status="skipped",
                    details="User rejected the approval request."
                )
            ]
        )


# Singleton instance
orchestrator = AgentOrchestrator()
