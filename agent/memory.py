"""
Persistent Personal Memory System for Ayush AI.
Loads and saves user preferences and notes to data/memory.json.
"""

import json
import datetime
from pathlib import Path
from typing import Dict, Any, List
from config import MEMORY_FILE
from agent.logger import logger

DEFAULT_MEMORY = {
    "name": "Ayush",
    "preferences": {
        "response_style": "simple and concise",
        "coding_style": "simple and understandable",
        "website_style": "modern and clean"
    },
    "custom_notes": [
        "Ayush is the user and developer.",
        "Prefers practical solutions, concise explanations, and structured tables."
    ],
    "last_updated": datetime.datetime.now().isoformat()
}


def load_memory() -> Dict[str, Any]:
    """Loads memory dictionary from disk, creating defaults if missing or corrupted."""
    if not MEMORY_FILE.exists():
        save_memory(DEFAULT_MEMORY)
        return DEFAULT_MEMORY.copy()
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return DEFAULT_MEMORY.copy()
            return data
    except Exception as e:
        logger.error(f"Failed to read memory file {MEMORY_FILE}: {e}. Resetting to defaults.")
        return DEFAULT_MEMORY.copy()


def save_memory(data: Dict[str, Any]) -> None:
    """Saves memory dictionary to disk."""
    try:
        data["last_updated"] = datetime.datetime.now().isoformat()
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Memory saved successfully.")
    except Exception as e:
        logger.error(f"Error writing memory to {MEMORY_FILE}: {e}")
        raise


def add_memory(key: str, value: Any) -> Dict[str, Any]:
    """Adds or updates a memory key or preference."""
    data = load_memory()
    key_clean = key.strip().lower()

    if key_clean in ("note", "custom_note", "custom_notes"):
        if "custom_notes" not in data:
            data["custom_notes"] = []
        if str(value) not in data["custom_notes"]:
            data["custom_notes"].append(str(value))
    elif key_clean in data.get("preferences", {}):
        data["preferences"][key_clean] = str(value)
    else:
        # Check if it should be added to preferences or general custom notes
        if "preferences" not in data:
            data["preferences"] = {}
        data["preferences"][key_clean] = str(value)

    save_memory(data)
    return data


def get_relevant_memory(query: str = "") -> str:
    """Formats personal memory into a clean prompt-ready context block."""
    data = load_memory()
    name = data.get("name", "Ayush")
    prefs = data.get("preferences", {})
    notes = data.get("custom_notes", [])

    lines = [f"User Name: {name}"]
    if prefs:
        lines.append("User Preferences:")
        for k, v in prefs.items():
            lines.append(f"  - {k.replace('_', ' ').capitalize()}: {v}")
    if notes:
        lines.append("Key Notes & Context:")
        for n in notes:
            lines.append(f"  - {n}")

    return "\n".join(lines)
