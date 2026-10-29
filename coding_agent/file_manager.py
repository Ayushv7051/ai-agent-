"""
Project File Manager for Coding Agent.
Creates folders, source files, and unit test suites inside workspace/.
"""

from pathlib import Path
from typing import Dict, Any, List
from config import WORKSPACE_DIR
from agent.file_ops import create_file, read_file, list_files
from agent.permissions import validate_safe_path
from agent.logger import logger


class ProjectFileManager:
    """Manages files and directories for a specific project within workspace/."""

    def __init__(self, project_name: str):
        self.project_name = project_name.strip().replace(" ", "_")
        self.project_dir = validate_safe_path(
            WORKSPACE_DIR / self.project_name,
            allowed_roots=[WORKSPACE_DIR]
        )
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def write_source_file(self, relative_path: str, content: str) -> Dict[str, Any]:
        """Writes a source file inside the project directory."""
        target_path = validate_safe_path(
            self.project_dir / relative_path,
            allowed_roots=[WORKSPACE_DIR]
        )
        return create_file(str(target_path), content)

    def read_source_file(self, relative_path: str) -> Dict[str, Any]:
        """Reads a source file inside the project directory."""
        target_path = validate_safe_path(
            self.project_dir / relative_path,
            allowed_roots=[WORKSPACE_DIR]
        )
        return read_file(str(target_path))

    def list_project_files(self) -> List[str]:
        """Returns relative paths of all project files."""
        res = []
        for p in self.project_dir.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                res.append(str(p.relative_to(self.project_dir)))
        return res
