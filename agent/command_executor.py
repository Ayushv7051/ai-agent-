"""
Restricted Development Command Executor for Ayush AI.
Allows safe execution of development commands (python, pip, node, npm, git, pytest)
strictly confined to the workspace/ sandbox with hard timeouts.
Blocks arbitrary shell scripts, cmd.exe, and powershell.exe escaping.
"""

import subprocess
import shlex
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import WORKSPACE_DIR
from agent.permissions import validate_safe_path, SecurityViolationError
from agent.logger import logger

# Strictly allowed executable binaries for development operations
ALLOWED_COMMANDS = {
    "python",
    "python.exe",
    "pytest",
    "pip",
    "node",
    "node.exe",
    "npm",
    "git",
}

# Dangerous argument patterns to block unconditionally
BLOCKED_ARG_PATTERNS = [
    r"rmdir\s+/s",
    r"format\s+",
    r"del\s+/f\s+/s\s+/q",
    r"powershell",
    r"cmd\.exe",
    r"bash",
    r"sh",
    r"curl\s+.*\s*\|\s*(sh|bash)",
    r":\(\)\s*\{",  # Fork bomb
]


def execute_sandboxed_command(
    command_str: str,
    cwd: Optional[Path] = None,
    timeout_seconds: int = 45
) -> Dict[str, Any]:
    """
    Safely executes an allowlisted development command inside WORKSPACE_DIR.
    """
    # 1. Determine & validate working directory
    target_cwd = (cwd or WORKSPACE_DIR).resolve()
    try:
        target_cwd = validate_safe_path(target_cwd, allowed_roots=[WORKSPACE_DIR])
    except SecurityViolationError as sve:
        return {
            "success": False,
            "result": None,
            "error": f"Working directory security violation: {str(sve)}",
            "verification": {"verified": False, "details": "Directory escaped sandbox."}
        }

    # 2. Tokenize command safely
    clean_cmd = command_str.strip()
    try:
        parts = shlex.split(clean_cmd, posix=True)
    except Exception:
        try:
            parts = shlex.split(clean_cmd, posix=False)
            parts = [p.strip('"\'') if (p.startswith(('"', "'")) and p.endswith(('"', "'"))) else p for p in parts]
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"Invalid command syntax: {str(e)}",
                "verification": {"verified": False, "details": "Syntax parse failure."}
            }

    if not parts:
        return {
            "success": False,
            "result": None,
            "error": "Empty command.",
            "verification": {"verified": False, "details": "No command provided."}
        }

    base_cmd = parts[0].lower().replace("/", "\\").split("\\")[-1]

    # 3. Check Command Allowlist
    if base_cmd not in ALLOWED_COMMANDS:
        logger.warning(f"Blocked unauthorized command invocation: '{base_cmd}'")
        return {
            "success": False,
            "result": None,
            "error": f"Command '{base_cmd}' is not in the development allowlist: {', '.join(sorted(ALLOWED_COMMANDS))}",
            "verification": {"verified": False, "details": "Blocked by allowlist policy."}
        }

    # 4. Check for blocked patterns in full string
    lower_full = clean_cmd.lower()
    for pattern in BLOCKED_ARG_PATTERNS:
        if pattern in lower_full:
            logger.warning(f"Blocked dangerous argument pattern '{pattern}' in command '{clean_cmd}'")
            return {
                "success": False,
                "result": None,
                "error": f"Command contains forbidden dangerous pattern: '{pattern}'",
                "verification": {"verified": False, "details": "Dangerous pattern detected."}
            }

    # 5. Execute with Timeout & Output Capture
    logger.info(f"Executing sandboxed command: '{clean_cmd}' in {target_cwd}")
    try:
        process = subprocess.run(
            parts,
            cwd=str(target_cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False
        )

        success = (process.returncode == 0)
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()

        return {
            "success": success,
            "result": {
                "command": clean_cmd,
                "exit_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "cwd": str(target_cwd)
            },
            "error": stderr if not success and not stdout else None,
            "verification": {
                "verified": success,
                "details": f"Process finished with exit code {process.returncode}."
            }
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Command '{clean_cmd}' timed out after {timeout_seconds} seconds.")
        return {
            "success": False,
            "result": None,
            "error": f"Command execution timed out after {timeout_seconds} seconds.",
            "verification": {"verified": False, "details": "Execution timeout expired."}
        }
    except Exception as e:
        logger.error(f"Command execution error: {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Failed to execute command: {str(e)}",
            "verification": {"verified": False, "details": "Subprocess execution failed."}
        }
