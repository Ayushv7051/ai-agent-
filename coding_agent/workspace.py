"""
Coding Agent Workspace Sandbox Manager (Scaffold for V2).
Manages safe file creation, modifications, tree indexing, and diff generation within workspace/.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import WORKSPACE_DIR


class CodeWorkspaceManager(ABC):
    """Abstract interface for managing files inside the workspace sandbox."""

    def __init__(self, root_dir: Path = WORKSPACE_DIR):
        self.root_dir = root_dir

    @abstractmethod
    def create_file(self, relative_path: str, content: str) -> Dict[str, Any]:
        """Creates a source file inside the workspace."""
        raise NotImplementedError("Coding Agent will be enabled in V2.")

    @abstractmethod
    def read_file(self, relative_path: str) -> str:
        """Reads contents of a file inside the workspace."""
        raise NotImplementedError("Coding Agent will be enabled in V2.")

    @abstractmethod
    def apply_diff(self, relative_path: str, diff_patch: str) -> bool:
        """Applies a targeted patch or surgical diff to an existing file."""
        raise NotImplementedError("Coding Agent will be enabled in V2.")

    @abstractmethod
    def list_files(self, subdirectory: Optional[str] = None) -> List[str]:
        """Lists files within the workspace sandbox."""
        raise NotImplementedError("Coding Agent will be enabled in V2.")
