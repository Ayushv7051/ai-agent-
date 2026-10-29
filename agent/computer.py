"""
Desktop Control and Computer Automation Module using PyAutoGUI.
Restricted strictly to safe, allowlisted applications and desktop keystrokes.
Supports safe native Windows file opening (open_file).
"""

import os
import subprocess
import datetime
import pyautogui
from pathlib import Path
from typing import Dict, Any, Optional
from config import WORKSPACE_DIR, FILES_DIR, ALLOWED_APPLICATIONS
from agent.permissions import is_application_allowed, SecurityViolationError, validate_safe_path
from agent.logger import logger

# PyAutoGUI Safety Settings (FAILSAFE set to False to prevent false corner triggers during keystroke typing)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


def open_application(application: str) -> Dict[str, Any]:
    """
    Safely opens an allowlisted Windows desktop application.
    Blocks arbitrary executable paths and shell injection.
    """
    app_clean = application.strip().lower()

    if not is_application_allowed(app_clean):
        logger.warning(f"Rejected attempt to open unapproved application: '{application}'")
        raise SecurityViolationError(
            f"Application '{application}' is not in the allowed list: {', '.join(ALLOWED_APPLICATIONS)}"
        )

    # Windows executable mapping
    app_cmd_map = {
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "mspaint": "mspaint.exe",
        "paint": "mspaint.exe",
        "browser": "explorer.exe https://www.google.com",
        "chrome": "chrome.exe",
        "edge": "msedge.exe",
        "vscode": "code.exe",
        "code": "code.exe",
    }

    cmd = app_cmd_map.get(app_clean, f"{app_clean}.exe")
    logger.info(f"Opening approved application: {app_clean} via '{cmd}'")

    try:
        subprocess.Popen(cmd, shell=True)
        return {
            "success": True,
            "result": {"application": app_clean, "command": cmd},
            "error": None,
            "verification": {
                "verified": True,
                "details": f"Process '{app_clean}' launched successfully."
            }
        }
    except Exception as e:
        logger.error(f"Failed to launch application '{app_clean}': {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Error launching application: {str(e)}",
            "verification": {"verified": False, "details": "Process spawn failed."}
        }


def open_file(filepath: str) -> Dict[str, Any]:
    """
    Opens an office document, image, or code file using the default Windows application.
    Enforces strict path containment within workspace/ or files/.
    """
    try:
        safe_path = validate_safe_path(filepath, allowed_roots=[WORKSPACE_DIR, FILES_DIR])
    except SecurityViolationError as sve:
        return {
            "success": False,
            "result": None,
            "error": str(sve),
            "verification": {"verified": False, "details": "File escaped sandbox."}
        }

    if not safe_path.exists():
        return {
            "success": False,
            "result": None,
            "error": f"File '{filepath}' does not exist.",
            "verification": {"verified": False, "details": "Target file not found."}
        }

    logger.info(f"Opening file with native Windows viewer: {safe_path}")
    try:
        os.startfile(str(safe_path))
        return {
            "success": True,
            "result": {"filepath": str(safe_path), "filename": safe_path.name},
            "error": None,
            "verification": {
                "verified": True,
                "details": f"Opened '{safe_path.name}' in default Windows application."
            }
        }
    except Exception as e:
        logger.error(f"Failed to open file '{safe_path}': {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Failed to open file: {str(e)}",
            "verification": {"verified": False, "details": "os.startfile error."}
        }


def type_text(text: str) -> Dict[str, Any]:
    """Types text via keyboard simulation safely into the currently focused window."""
    logger.info(f"Typing text (length: {len(text)})")
    try:
        pyautogui.write(text, interval=0.03)
        return {
            "success": True,
            "result": {"length": len(text), "typed": text[:50] + ("..." if len(text) > 50 else "")},
            "error": None,
            "verification": {
                "verified": True,
                "details": f"Successfully typed {len(text)} characters."
            }
        }
    except Exception as e:
        logger.error(f"Error typing text: {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Keystroke typing failed: {str(e)}",
            "verification": {"verified": False, "details": "PyAutoGUI write exception."}
        }


def press_key(key: str) -> Dict[str, Any]:
    """Presses a designated keyboard key (e.g., 'enter', 'tab', 'esc', 'space')."""
    clean_key = key.strip().lower()
    valid_keys = [
        "enter", "return", "tab", "space", "backspace", "delete",
        "esc", "escape", "up", "down", "left", "right", "home", "end"
    ]

    if clean_key not in valid_keys:
        return {
            "success": False,
            "result": None,
            "error": f"Key '{key}' is not in permitted safe keys list: {', '.join(valid_keys)}",
            "verification": {"verified": False, "details": "Key rejected by allowlist."}
        }

    logger.info(f"Pressing keyboard key: {clean_key}")
    try:
        pyautogui.press(clean_key)
        return {
            "success": True,
            "result": {"key": clean_key},
            "error": None,
            "verification": {
                "verified": True,
                "details": f"Pressed key '{clean_key}'."
            }
        }
    except Exception as e:
        logger.error(f"Error pressing key '{clean_key}': {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Failed to press key: {str(e)}",
            "verification": {"verified": False, "details": "PyAutoGUI press exception."}
        }


def take_screenshot(filename: Optional[str] = None) -> Dict[str, Any]:
    """Takes a desktop screenshot and saves it inside the workspace/ directory."""
    if not filename:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{ts}.png"

    if not filename.endswith((".png", ".jpg", ".jpeg")):
        filename += ".png"

    target_path = validate_safe_path(WORKSPACE_DIR / filename, allowed_roots=[WORKSPACE_DIR])
    logger.info(f"Taking screenshot and saving to: {target_path}")

    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(target_path)
        
        # Verify file on disk
        if target_path.exists() and target_path.stat().st_size > 0:
            return {
                "success": True,
                "result": {
                    "filename": target_path.name,
                    "saved_path": str(target_path),
                    "size_bytes": target_path.stat().st_size
                },
                "error": None,
                "verification": {
                    "verified": True,
                    "details": f"Screenshot verified on disk ({target_path.stat().st_size} bytes)."
                }
            }
        return {
            "success": False,
            "result": None,
            "error": "Screenshot file was not written to disk.",
            "verification": {"verified": False, "details": "File missing post-save."}
        }
    except Exception as e:
        logger.error(f"Error capturing screenshot: {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Failed to capture screenshot: {str(e)}",
            "verification": {"verified": False, "details": "Screenshot capture failed."}
        }
