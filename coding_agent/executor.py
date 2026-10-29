"""
Project Executor for Coding Agent.
Executes code files inside a project directory using the sandboxed command executor.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from config import WORKSPACE_DIR
from agent.command_executor import execute_sandboxed_command
from agent.logger import logger


class ProjectExecutor:
    """Executes code scripts within a sandboxed project directory."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def run_entrypoint(self, entrypoint_file: str = "main.py", args: str = "") -> Dict[str, Any]:
        """Runs the main entrypoint file with Python."""
        cmd = f"python {entrypoint_file} {args}".strip()
        logger.info(f"Coding Agent executing: {cmd} in {self.project_dir.name}")
        return execute_sandboxed_command(cmd, cwd=self.project_dir, timeout_seconds=30)

    def run_command(self, cmd_str: str) -> Dict[str, Any]:
        """Runs an arbitrary allowlisted command in the project directory."""
        return execute_sandboxed_command(cmd_str, cwd=self.project_dir, timeout_seconds=45)
