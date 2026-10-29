"""
Permission and Security System for Ayush AI.
Enforces strict path containment, safe application allowlists, and a real
approval lifecycle for potentially dangerous actions.
"""

import os
import uuid
import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from config import BASE_DIR, WORKSPACE_DIR, FILES_DIR, ALLOWED_APPLICATIONS
from agent.schemas import PendingApproval
from agent.logger import logger

# Blocked sensitive Windows directory fragments
BLOCKED_SYSTEM_PATHS = [
    r"c:\windows",
    r"c:\system32",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\users\all users",
    r"c:\recovery",
    r"c:\boot",
    r"system volume information",
]

# In-memory approval storage (backed by SQLite in db.py as well)
_PENDING_APPROVALS: Dict[str, PendingApproval] = {}


class SecurityViolationError(Exception):
    """Raised when an operation violates path containment or security guardrails."""
    pass


def validate_safe_path(target_path: str | Path, allowed_roots: Optional[List[Path]] = None) -> Path:
    """
    Validates that a path resides strictly within the approved workspace or files sandbox.
    Prevents directory traversal, symlink escapes, and attempts to touch sensitive Windows paths.
    """
    if not allowed_roots:
        allowed_roots = [WORKSPACE_DIR.resolve(), FILES_DIR.resolve()]
    else:
        allowed_roots = [r.resolve() for r in allowed_roots]

    # Convert to Path and resolve
    raw_str = str(target_path).strip()
    norm_lower = raw_str.lower().replace("/", "\\")

    # Check for explicit system paths
    for blocked in BLOCKED_SYSTEM_PATHS:
        if blocked in norm_lower:
            logger.warning(f"Security Alert: Blocked attempt to access sensitive system path: {raw_str}")
            raise SecurityViolationError(f"Access to protected system path '{raw_str}' is strictly forbidden.")

    # Resolve relative paths against WORKSPACE_DIR
    target = Path(target_path)
    if not target.is_absolute():
        target = (WORKSPACE_DIR / target).resolve()
    else:
        target = target.resolve()

    # Verify containment within at least one allowed root
    contained = False
    for root in allowed_roots:
        try:
            # Commonpath comparison handles subpaths safely across Windows drives
            common = Path(os.path.commonpath([root, target])).resolve()
            if common == root:
                contained = True
                break
        except (ValueError, OSError):
            continue

    if not contained:
        logger.warning(f"Security Alert: Path traversal attempt outside sandbox: {target}")
        raise SecurityViolationError(
            f"Path '{target_path}' is outside the permitted directories ({WORKSPACE_DIR} or {FILES_DIR})."
        )

    return target


def is_application_allowed(app_name: str) -> bool:
    """Checks if the requested application is in the safe allowlist."""
    norm = app_name.strip().lower()
    return norm in ALLOWED_APPLICATIONS


# ---------------------------------------------------------
# Approval Manager
# ---------------------------------------------------------

def create_pending_approval(tool: str, arguments: dict, reason: str) -> PendingApproval:
    """Creates a new pending approval object with a unique UUID."""
    approval_id = str(uuid.uuid4())
    item = PendingApproval(
        id=approval_id,
        tool=tool,
        arguments=arguments,
        reason=reason,
        status="pending",
        created_at=datetime.datetime.now().isoformat()
    )
    _PENDING_APPROVALS[approval_id] = item
    logger.info(f"Created pending approval [{approval_id}] for tool '{tool}': {reason}")
    return item


def get_pending_approval(approval_id: str) -> Optional[PendingApproval]:
    """Retrieves an existing approval by ID."""
    return _PENDING_APPROVALS.get(approval_id)


def list_pending_approvals() -> List[PendingApproval]:
    """Returns all currently pending approvals."""
    return [item for item in _PENDING_APPROVALS.values() if item.status == "pending"]


def approve_action(approval_id: str) -> Tuple[bool, Optional[PendingApproval]]:
    """Marks a pending action as approved."""
    if approval_id not in _PENDING_APPROVALS:
        return False, None
    item = _PENDING_APPROVALS[approval_id]
    if item.status != "pending":
        return False, item
    item.status = "approved"
    logger.info(f"Pending approval [{approval_id}] APPROVED for tool '{item.tool}'")
    return True, item


def reject_action(approval_id: str) -> Tuple[bool, Optional[PendingApproval]]:
    """Marks a pending action as rejected."""
    if approval_id not in _PENDING_APPROVALS:
        return False, None
    item = _PENDING_APPROVALS[approval_id]
    if item.status != "pending":
        return False, item
    item.status = "rejected"
    logger.info(f"Pending approval [{approval_id}] REJECTED for tool '{item.tool}'")
    return True, item
