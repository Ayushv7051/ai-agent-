"""
Sandboxed File Operations for Ayush AI.
Enforces strict path containment inside workspace/ and files/.
Every write and creation action automatically verifies on-disk state.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from config import WORKSPACE_DIR, FILES_DIR
from agent.permissions import validate_safe_path, SecurityViolationError
from agent.logger import logger


def list_files(directory: Optional[str] = None) -> Dict[str, Any]:
    """Lists files and folders inside a sandboxed directory."""
    target_dir = Path(directory) if directory else WORKSPACE_DIR
    try:
        safe_dir = validate_safe_path(target_dir, allowed_roots=[WORKSPACE_DIR, FILES_DIR])
    except SecurityViolationError as sve:
        return {
            "success": False,
            "result": None,
            "error": str(sve),
            "verification": {"verified": False, "details": "Path escaped sandbox."}
        }

    if not safe_dir.exists() or not safe_dir.is_dir():
        return {
            "success": False,
            "result": None,
            "error": f"Directory '{directory}' does not exist.",
            "verification": {"verified": False, "details": "Directory not found."}
        }

    items = []
    for entry in safe_dir.iterdir():
        if entry.name.startswith("."):
            continue
        stat = entry.stat()
        items.append({
            "name": entry.name,
            "type": "directory" if entry.is_dir() else "file",
            "size_bytes": stat.st_size if entry.is_file() else 0,
            "relative_path": str(entry.relative_to(safe_dir))
        })

    return {
        "success": True,
        "result": {
            "directory": str(safe_dir),
            "items": items,
            "total_items": len(items)
        },
        "error": None,
        "verification": {"verified": True, "details": f"Found {len(items)} items in {safe_dir.name}."}
    }


def read_file(filepath: str, max_chars: int = 8000) -> Dict[str, Any]:
    """Reads a text file securely from within the sandbox."""
    try:
        safe_file = validate_safe_path(filepath, allowed_roots=[WORKSPACE_DIR, FILES_DIR])
    except SecurityViolationError as sve:
        return {
            "success": False,
            "result": None,
            "error": str(sve),
            "verification": {"verified": False, "details": "Path containment violated."}
        }

    if not safe_file.exists() or not safe_file.is_file():
        return {
            "success": False,
            "result": None,
            "error": f"File '{filepath}' not found.",
            "verification": {"verified": False, "details": "File does not exist."}
        }

    try:
        content = safe_file.read_text(encoding="utf-8", errors="replace")
        truncated = content[:max_chars]
        is_trunc = len(content) > max_chars

        return {
            "success": True,
            "result": {
                "filepath": str(safe_file),
                "content": truncated,
                "is_truncated": is_trunc,
                "total_chars": len(content)
            },
            "error": None,
            "verification": {"verified": True, "details": f"Read {len(truncated)} characters successfully."}
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"Error reading file: {str(e)}",
            "verification": {"verified": False, "details": "Read I/O error."}
        }


def create_file(filepath: str, content: str = "") -> Dict[str, Any]:
    """Creates a new file with parent directories, verifying file creation."""
    try:
        safe_file = validate_safe_path(filepath, allowed_roots=[WORKSPACE_DIR, FILES_DIR])
    except SecurityViolationError as sve:
        return {
            "success": False,
            "result": None,
            "error": str(sve),
            "verification": {"verified": False, "details": "Path escaped sandbox."}
        }

    try:
        safe_file.parent.mkdir(parents=True, exist_ok=True)
        safe_file.write_text(content, encoding="utf-8")

        # Verify creation
        if not safe_file.exists():
            return {
                "success": False,
                "result": None,
                "error": "File was not detected on disk after write.",
                "verification": {"verified": False, "details": "Post-write verification failed."}
            }

        size = safe_file.stat().st_size
        return {
            "success": True,
            "result": {
                "filepath": str(safe_file),
                "filename": safe_file.name,
                "size_bytes": size
            },
            "error": None,
            "verification": {
                "verified": True,
                "details": f"File verified on disk ({size} bytes) at {safe_file.name}."
            }
        }
    except Exception as e:
        logger.error(f"Error creating file '{filepath}': {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Failed to create file: {str(e)}",
            "verification": {"verified": False, "details": "Creation error."}
        }


def write_file(filepath: str, content: str) -> Dict[str, Any]:
    """Overwrites or updates an existing file, verifying contents written."""
    return create_file(filepath, content)


def move_file(source: str, destination: str) -> Dict[str, Any]:
    """Moves a file safely within permitted sandbox roots."""
    try:
        safe_src = validate_safe_path(source, allowed_roots=[WORKSPACE_DIR, FILES_DIR])
        safe_dst = validate_safe_path(destination, allowed_roots=[WORKSPACE_DIR, FILES_DIR])
    except SecurityViolationError as sve:
        return {
            "success": False,
            "result": None,
            "error": str(sve),
            "verification": {"verified": False, "details": "Sandbox boundary violated."}
        }

    if not safe_src.exists():
        return {
            "success": False,
            "result": None,
            "error": f"Source file '{source}' does not exist.",
            "verification": {"verified": False, "details": "Source not found."}
        }

    try:
        safe_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(safe_src), str(safe_dst))

        # Verify on disk
        if safe_dst.exists() and not safe_src.exists():
            return {
                "success": True,
                "result": {"from": str(safe_src), "to": str(safe_dst)},
                "error": None,
                "verification": {"verified": True, "details": f"Verified move to {safe_dst.name}."}
            }
        else:
            return {
                "success": False,
                "result": None,
                "error": "Move verification check failed.",
                "verification": {"verified": False, "details": "File state inconsistent after move."}
            }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"Move failed: {str(e)}",
            "verification": {"verified": False, "details": "I/O error during move."}
        }


def copy_file(source: str, destination: str) -> Dict[str, Any]:
    """Copies a file safely within permitted sandbox roots."""
    try:
        safe_src = validate_safe_path(source, allowed_roots=[WORKSPACE_DIR, FILES_DIR])
        safe_dst = validate_safe_path(destination, allowed_roots=[WORKSPACE_DIR, FILES_DIR])
    except SecurityViolationError as sve:
        return {
            "success": False,
            "result": None,
            "error": str(sve),
            "verification": {"verified": False, "details": "Sandbox boundary violated."}
        }

    if not safe_src.exists():
        return {
            "success": False,
            "result": None,
            "error": f"Source file '{source}' does not exist.",
            "verification": {"verified": False, "details": "Source not found."}
        }

    try:
        safe_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(safe_src), str(safe_dst))

        if safe_dst.exists():
            return {
                "success": True,
                "result": {"from": str(safe_src), "to": str(safe_dst), "size": safe_dst.stat().st_size},
                "error": None,
                "verification": {"verified": True, "details": f"Verified copy created at {safe_dst.name}."}
            }
        return {
            "success": False,
            "result": None,
            "error": "Copy verification check failed.",
            "verification": {"verified": False, "details": "Destination missing after copy."}
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"Copy failed: {str(e)}",
            "verification": {"verified": False, "details": "I/O error during copy."}
        }
