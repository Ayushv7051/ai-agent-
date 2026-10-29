"""
Automated Test Runner for Coding Agent.
Executes test files and parses test outcomes.
"""

from pathlib import Path
from typing import Dict, Any
from agent.command_executor import execute_sandboxed_command
from agent.logger import logger


class ProjectTester:
    """Executes unit tests and collects pass/fail metrics."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def run_unittest(self, test_pattern: str = "test_*.py") -> Dict[str, Any]:
        """Runs python -m unittest inside the project directory."""
        cmd = f"python -m unittest discover -p {test_pattern}"
        logger.info(f"Running unit tests in {self.project_dir.name}: {cmd}")
        exec_res = execute_sandboxed_command(cmd, cwd=self.project_dir, timeout_seconds=30)
        
        output = ""
        if exec_res.get("result"):
            output = exec_res["result"].get("stdout", "") + "\n" + exec_res["result"].get("stderr", "")

        passed = exec_res.get("success", False) and ("FAILED" not in output)
        return {
            "passed": passed,
            "raw_output": output,
            "exit_code": exec_res.get("result", {}).get("exit_code", -1),
            "verification": {
                "verified": passed,
                "details": "All unit tests passed cleanly." if passed else "Unit test assertions failed."
            }
        }
