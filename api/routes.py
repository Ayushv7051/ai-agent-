"""
FastAPI Routes for Ayush AI.
Endpoints for chat, decoupled health check, personal memory,
file indexation, and real pending approvals.
"""

import os
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import WORD_DIR, EXCEL_DIR, PPT_DIR, WORKSPACE_DIR, OLLAMA_MODEL
from agent.brain import check_ollama
from agent.memory import load_memory, add_memory
from agent.orchestrator import orchestrator
from agent.permissions import list_pending_approvals, get_pending_approval
from agent.schemas import ChatRequest, ChatResponse, SaveMemoryInput, PendingApproval
from database.db import save_message, get_recent_messages, log_tool_execution
from agent.logger import logger

router = APIRouter()


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """
    Decoupled health endpoint reporting API status independently of Ollama.
    The application remains healthy even if Ollama is offline or restarting.
    """
    ollama_ok, ollama_msg, ollama_details = check_ollama()
    return {
        "status": "ok",
        "app": "Ayush AI",
        "version": "1.0.0",
        "timestamp": datetime.datetime.now().isoformat(),
        "ollama": {
            "connected": ollama_ok,
            "message": ollama_msg,
            "configured_model": OLLAMA_MODEL,
            "details": ollama_details
        }
    }


@router.post("/chat", response_model=ChatResponse)
def handle_chat(payload: ChatRequest, session_id: Optional[str] = "default") -> ChatResponse:
    """
    Main chat endpoint. Accepts natural language requests, manages tool executions,
    records conversation history in SQLite, and returns structured agent output.
    """
    user_msg = payload.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    logger.info(f"API /chat request received: '{user_msg}' (session: {session_id})")

    # Load conversation context from SQLite
    history = get_recent_messages(session_id=session_id, limit=6)
    history_formatted = [{"role": h["role"], "content": h["content"]} for h in history]

    # Run orchestrator
    result = orchestrator.run(user_message=user_msg, conversation_history=history_formatted)

    # Save user message and AI response to SQLite
    save_message(session_id=session_id, role="user", content=user_msg)
    save_message(session_id=session_id, role="assistant", content=result.response)

    # Log tool activities in SQLite
    for act in result.tool_activities:
        log_tool_execution(
            session_id=session_id,
            tool_name=act.tool,
            arguments={"action": act.action},
            status=act.status,
            result=act.details
        )

    return result


@router.get("/memory")
def get_memory() -> Dict[str, Any]:
    """Retrieves full personal memory content."""
    return load_memory()


@router.post("/memory")
def update_memory(item: SaveMemoryInput) -> Dict[str, Any]:
    """Updates or adds personal memory preferences."""
    updated = add_memory(key=item.key, value=item.value)
    return {"success": True, "memory": updated}


# ---------------------------------------------------------
# Approval Workflow Endpoints
# ---------------------------------------------------------

@router.get("/approvals/pending", response_model=List[PendingApproval])
def get_pending_approvals_list() -> List[PendingApproval]:
    """Returns all currently pending human approvals."""
    return list_pending_approvals()


@router.post("/approvals/{approval_id}/approve", response_model=ChatResponse)
def approve_request(approval_id: str) -> ChatResponse:
    """Explicitly approves a pending dangerous action and triggers its execution."""
    logger.info(f"Approval endpoint invoked for ID: {approval_id}")
    return orchestrator.execute_approved_action(approval_id)


@router.post("/approvals/{approval_id}/reject", response_model=ChatResponse)
def reject_request(approval_id: str) -> ChatResponse:
    """Explicitly rejects a pending action."""
    logger.info(f"Rejection endpoint invoked for ID: {approval_id}")
    return orchestrator.reject_pending_action(approval_id)


# ---------------------------------------------------------
# Generated Files Directory Index
# ---------------------------------------------------------

@router.get("/files")
def list_generated_files() -> Dict[str, Any]:
    """Lists created Word, Excel, PowerPoint documents, and workspace artifacts."""
    def _scan(directory: Path, file_type: str, url_prefix: str):
        files_list = []
        if directory.exists():
            for f in directory.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    stat = f.stat()
                    files_list.append({
                        "name": f.name,
                        "type": file_type,
                        "size_kb": round(stat.st_size / 1024, 2),
                        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "download_url": f"{url_prefix}/{f.name}"
                    })
        return files_list

    return {
        "word_documents": _scan(WORD_DIR, "word", "/files/word"),
        "excel_spreadsheets": _scan(EXCEL_DIR, "excel", "/files/excel"),
        "powerpoint_presentations": _scan(PPT_DIR, "ppt", "/files/ppt"),
        "workspace_files": _scan(WORKSPACE_DIR, "workspace", "/workspace/file")
    }
