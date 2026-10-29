"""
Security, Guardrails, and Permission Tests for Ayush AI.
Specifically validates:
- Path traversal prevention
- Blocked system directories
- Blocked arbitrary shell commands
- Approval-required actions
- Rejected approvals
- Invalid tool arguments
- Agent iteration limits
- Tool execution timeouts
"""

import sys
import unittest
import time
from pathlib import Path

# Ensure project root is dynamically in sys.path when running directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.permissions import (
    validate_safe_path,
    SecurityViolationError,
    create_pending_approval,
    get_pending_approval,
    approve_action,
    reject_action
)
from agent.tools import execute_tool, REGISTRY, ToolDefinition
from agent.schemas import WebSearchInput
from agent.orchestrator import AgentOrchestrator
from config import WORKSPACE_DIR, FILES_DIR


class TestAgentSecurity(unittest.TestCase):

    def test_01_path_traversal_prevention(self):
        """Tests that relative and parent directory traversal attempts are blocked."""
        with self.assertRaises(SecurityViolationError):
            validate_safe_path("../secret_system_file.txt")

        with self.assertRaises(SecurityViolationError):
            validate_safe_path("..\\..\\..\\Users\\other_user\\passwords.txt")

        # Allowed subpath within WORKSPACE_DIR
        valid_path = validate_safe_path("my_project/code.py")
        self.assertTrue(str(valid_path).startswith(str(WORKSPACE_DIR.resolve())))

    def test_02_blocked_system_directories(self):
        """Tests that sensitive Windows directories are strictly forbidden."""
        blocked_targets = [
            r"C:\Windows\System32\cmd.exe",
            r"C:\Windows\explorer.exe",
            r"C:\Program Files\App\setup.exe",
            r"C:\Program Files (x86)\Common\secret.dll"
        ]
        for target in blocked_targets:
            with self.assertRaises(SecurityViolationError):
                validate_safe_path(target)

    def test_03_blocked_arbitrary_shell_commands(self):
        """Verifies that arbitrary shell execution tools are blocked."""
        res1 = execute_tool("run_shell_command", {"command": "dir"})
        self.assertFalse(res1["success"])
        self.assertIn("blocked", res1["error"].lower())

        res2 = execute_tool("powershell", {"script": "Get-Process"})
        self.assertFalse(res2["success"])
        self.assertIn("blocked", res2["error"].lower())

    def test_04_approval_required_workflow(self):
        """Tests that dangerous operations generate a pending approval with unique ID."""
        res = execute_tool("delete_file", {"filepath": "workspace/dummy.txt"})
        self.assertEqual(res.get("status"), "pending_approval")
        self.assertIn("approval_id", res)
        appr_id = res["approval_id"]

        pending_obj = get_pending_approval(appr_id)
        self.assertIsNotNone(pending_obj)
        self.assertEqual(pending_obj.status, "pending")

    def test_05_rejected_approval_handling(self):
        """Tests rejecting an approval updates status and prevents execution."""
        appr = create_pending_approval("test_dangerous_tool", {}, "Testing rejection")
        success, rejected_item = reject_action(appr.id)
        self.assertTrue(success)
        self.assertEqual(rejected_item.status, "rejected")

        # Re-rejecting or re-approving a closed approval must fail
        success2, _ = approve_action(appr.id)
        self.assertFalse(success2)

    def test_06_invalid_tool_arguments(self):
        """Tests that invalid parameters are rejected by strict Pydantic schemas."""
        # max_results exceeds ge=1, le=20 limit
        res = execute_tool("web_search", {"query": "test", "max_results": 9999})
        self.assertFalse(res["success"])
        self.assertIn("Invalid arguments", res["error"])

        # Missing required 'query'
        res2 = execute_tool("web_search", {"max_results": 5})
        self.assertFalse(res2["success"])
        self.assertIn("Invalid arguments", res2["error"])

    def test_07_agent_iteration_limit(self):
        """Tests that the orchestrator enforces maximum loop iterations (8)."""
        orch = AgentOrchestrator(max_iterations=3)
        self.assertEqual(orch.max_iterations, 3)

    def test_08_tool_execution_timeout(self):
        """Tests that a tool exceeding timeout limit is cleanly terminated."""
        def _slow_tool_handler(args):
            time.sleep(4)
            return "finished"

        # Register a temporary slow tool definition
        slow_tool = ToolDefinition(
            name="_unit_test_slow_tool",
            description="Simulates slow task",
            schema=WebSearchInput,
            handler=_slow_tool_handler
        )
        REGISTRY["_unit_test_slow_tool"] = slow_tool

        try:
            # Execute with a 1-second timeout
            res = execute_tool("_unit_test_slow_tool", {"query": "test"}, timeout_seconds=1)
            self.assertFalse(res["success"])
            self.assertIn("timed out", res["error"].lower())
        finally:
            REGISTRY.pop("_unit_test_slow_tool", None)

    def test_09_interactive_cli_approval(self):
        """Tests that interactive approval callback properly approves or halts dangerous tools."""
        from agent.file_ops import create_file
        test_f = "test_to_delete.txt"
        create_file(test_f, "test content")

        # 1. Reject callback
        reject_res = execute_tool("delete_file", {"filepath": test_f}, approval_callback=lambda a: False)
        self.assertFalse(reject_res["success"])
        self.assertIn("rejected", reject_res["error"].lower())
        self.assertTrue((WORKSPACE_DIR / test_f).exists())

        # 2. Approve callback
        approve_res = execute_tool("delete_file", {"filepath": test_f}, approval_callback=lambda a: True)
        self.assertTrue(approve_res["success"])
        self.assertFalse((WORKSPACE_DIR / test_f).exists())


if __name__ == "__main__":
    unittest.main()
