"""
Error Diagnostic and Debugger for Coding Agent.
Parses stack traces, extracts assertion failures, and prepares corrective suggestions.
"""

import re
from typing import Dict, Any, List


class ProjectDebugger:
    """Parses execution errors to extract failing files and lines."""

    @staticmethod
    def parse_traceback(error_text: str) -> Dict[str, Any]:
        """Extracts error type, message, and failing line numbers."""
        lines = error_text.splitlines()
        error_type = "UnknownError"
        error_msg = error_text
        failing_files = []

        # Find traceback lines: File "...", line X, in ...
        matches = re.findall(r'File "([^"]+)", line (\d+)', error_text)
        for fpath, lnum in matches:
            failing_files.append({"file": fpath, "line": int(lnum)})

        # Find final error line: NameError: name 'x' is not defined
        for line in reversed(lines):
            line_str = line.strip()
            if ":" in line_str and not line_str.startswith("File"):
                parts = line_str.split(":", 1)
                error_type = parts[0].strip()
                error_msg = parts[1].strip()
                break

        return {
            "error_type": error_type,
            "error_message": error_msg,
            "trace_frames": failing_files,
            "has_error": bool(error_text.strip())
        }
