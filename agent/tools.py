"""
Central Tool Registry and Dispatcher for Ayush AI.
Enforces strict Pydantic validation, execution timeouts, approval interceptors,
and generates schemas for Ollama tool calling.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Dict, Any, Callable, List, Type, Optional
from pathlib import Path
from pydantic import BaseModel, ValidationError

from config import TOOL_TIMEOUT_SECONDS, WORKSPACE_DIR
from agent.logger import logger
from agent.schemas import (
    WebSearchInput,
    ResearchWebpageInput,
    OpenUrlInput,
    BrowserOpenInput,
    BrowserSearchInput,
    BrowserClickInput,
    BrowserTypeInput,
    BrowserExtractInput,
    BrowserScreenshotInput,
    OpenApplicationInput,
    OpenFileInput,
    TypeTextInput,
    PressKeyInput,
    TakeScreenshotInput,
    ListFilesInput,
    ReadFileInput,
    CreateFileInput,
    WriteFileInput,
    MoveFileInput,
    CopyFileInput,
    DeleteFileInput,
    CreateWordInput,
    CreateExcelInput,
    CreatePowerPointInput,
    CreateCodingProjectInput,
    RunProjectCodeInput,
    RememberInput,
    RecallInput,
    CheckStatusInput,
)
from agent.search import web_search, web_research
from agent.browser import (
    browser_open,
    browser_search,
    browser_extract,
    browser_screenshot
)
from agent.computer import (
    open_application,
    open_file,
    type_text,
    press_key,
    take_screenshot
)
from agent.file_ops import (
    list_files,
    read_file,
    create_file,
    write_file,
    move_file,
    copy_file
)
from agent.documents import create_word
from agent.excel import create_excel
from agent.powerpoint import create_powerpoint
from agent.memory import add_memory, get_relevant_memory, load_memory
from agent.command_executor import execute_sandboxed_command
from agent.brain import check_ollama
from agent.permissions import (
    create_pending_approval,
    validate_safe_path,
    SecurityViolationError
)
import coding_agent


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        schema: Type[BaseModel],
        handler: Callable,
        permission_level: str = "SAFE"
    ):
        self.name = name
        self.description = description
        self.schema = schema
        self.handler = handler
        self.permission_level = permission_level

    @property
    def requires_approval(self) -> bool:
        return self.permission_level in ("CONFIRM", "DANGEROUS")

    def to_ollama_tool(self) -> Dict[str, Any]:
        """Converts Pydantic model to Ollama / OpenAI function calling schema."""
        json_schema = self.schema.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": json_schema.get("properties", {}),
                    "required": json_schema.get("required", [])
                }
            }
        }


# ---------------------------------------------------------
# Helper Handlers
# ---------------------------------------------------------

def _delete_file_handler(filepath: str) -> Dict[str, Any]:
    safe_path = validate_safe_path(filepath, allowed_roots=[WORKSPACE_DIR])
    if safe_path.is_file():
        safe_path.unlink()
        return {
            "success": True,
            "result": {"deleted_file": str(safe_path)},
            "error": None,
            "verification": {"verified": not safe_path.exists(), "details": f"File '{safe_path.name}' deleted."}
        }
    elif safe_path.is_dir():
        import shutil
        shutil.rmtree(str(safe_path))
        return {
            "success": True,
            "result": {"deleted_directory": str(safe_path)},
            "error": None,
            "verification": {"verified": not safe_path.exists(), "details": f"Directory '{safe_path.name}' removed."}
        }
    return {
        "success": False,
        "result": None,
        "error": f"Target '{filepath}' not found.",
        "verification": {"verified": False, "details": "Path missing."}
    }


def _check_status_handler(detail: bool = False) -> Dict[str, Any]:
    ollama_ok, msg, details = check_ollama()
    from config import OLLAMA_MODEL, WORKSPACE_DIR, FILES_DIR
    res = {
        "ollama": "Connected" if ollama_ok else "Disconnected",
        "model": OLLAMA_MODEL,
        "tools_count": len(REGISTRY),
        "workspace": str(WORKSPACE_DIR),
        "files_dir": str(FILES_DIR),
        "memory": "Enabled"
    }
    if detail:
        res["ollama_details"] = details
    return {
        "success": True,
        "result": res,
        "error": None,
        "verification": {"verified": True, "details": "System status collected."}
    }


# ---------------------------------------------------------
# Central Tool Registry
# ---------------------------------------------------------

REGISTRY: Dict[str, ToolDefinition] = {
    # Web & Search
    "web_search": ToolDefinition(
        name="web_search",
        description="Search DuckDuckGo/Internet for live information, news, and jobs.",
        schema=WebSearchInput,
        handler=lambda a: {"success": True, "result": web_search(a["query"], a.get("max_results", 5)), "error": None, "verification": {"verified": True, "details": "Web search returned."}},
        permission_level="SAFE"
    ),
    "research_webpage": ToolDefinition(
        name="research_webpage",
        description="Perform in-depth web research on a specific URL or topic.",
        schema=ResearchWebpageInput,
        handler=lambda a: {"success": True, "result": web_research(a["url"]), "error": None, "verification": {"verified": True, "details": "Web research analyzed."}},
        permission_level="SAFE"
    ),
    "open_url": ToolDefinition(
        name="open_url",
        description="Open a web URL in the browser.",
        schema=OpenUrlInput,
        handler=lambda a: browser_open(url=a["url"], headless=False),
        permission_level="SAFE"
    ),

    # Browser Automation (Playwright)
    "browser_open": ToolDefinition(
        name="browser_open",
        description="Launch Playwright browser and open a web URL.",
        schema=BrowserOpenInput,
        handler=lambda a: browser_open(url=a["url"], headless=a.get("headless", False)),
        permission_level="SAFE"
    ),
    "browser_search": ToolDefinition(
        name="browser_search",
        description="Perform an interactive Google search in the browser.",
        schema=BrowserSearchInput,
        handler=lambda a: browser_search(query=a["query"]),
        permission_level="SAFE"
    ),
    "browser_extract": ToolDefinition(
        name="browser_extract",
        description="Extract visible text or container content from a webpage.",
        schema=BrowserExtractInput,
        handler=lambda a: browser_extract(url=a["url"], selector=a.get("selector")),
        permission_level="SAFE"
    ),
    "browser_screenshot": ToolDefinition(
        name="browser_screenshot",
        description="Take a screenshot of a webpage and save to workspace/.",
        schema=BrowserScreenshotInput,
        handler=lambda a: browser_screenshot(url=a["url"], filename=a.get("filename")),
        permission_level="SAFE"
    ),

    # Computer & Desktop Controls
    "open_application": ToolDefinition(
        name="open_application",
        description="Open an allowlisted Windows app (notepad, calc, paint, chrome, edge, vscode).",
        schema=OpenApplicationInput,
        handler=lambda a: open_application(application=a["application"]),
        permission_level="SAFE"
    ),
    "open_file": ToolDefinition(
        name="open_file",
        description="Open an office document (.docx, .xlsx, .pptx) or screenshot in default Windows application.",
        schema=OpenFileInput,
        handler=lambda a: open_file(filepath=a["filepath"]),
        permission_level="SAFE"
    ),
    "type_text": ToolDefinition(
        name="type_text",
        description="Type text via keyboard into the currently active window.",
        schema=TypeTextInput,
        handler=lambda a: type_text(text=a["text"]),
        permission_level="SAFE"
    ),
    "press_key": ToolDefinition(
        name="press_key",
        description="Press a keyboard key (enter, esc, tab, space).",
        schema=PressKeyInput,
        handler=lambda a: press_key(key=a["key"]),
        permission_level="SAFE"
    ),
    "take_screenshot": ToolDefinition(
        name="take_screenshot",
        description="Capture full desktop screenshot and save to workspace/.",
        schema=TakeScreenshotInput,
        handler=lambda a: take_screenshot(filename=a.get("filename")),
        permission_level="SAFE"
    ),

    # Sandboxed Filesystem
    "list_files": ToolDefinition(
        name="list_files",
        description="List files in a sandboxed directory inside workspace/ or files/.",
        schema=ListFilesInput,
        handler=lambda a: list_files(directory=a.get("directory")),
        permission_level="SAFE"
    ),
    "read_file": ToolDefinition(
        name="read_file",
        description="Read the contents of a text file inside workspace/ or files/.",
        schema=ReadFileInput,
        handler=lambda a: read_file(filepath=a["filepath"]),
        permission_level="SAFE"
    ),
    "create_file": ToolDefinition(
        name="create_file",
        description="Create a file inside workspace/ with initial content.",
        schema=CreateFileInput,
        handler=lambda a: create_file(filepath=a["filepath"], content=a.get("content", "")),
        permission_level="SAFE"
    ),
    "write_file": ToolDefinition(
        name="write_file",
        description="Write or overwrite content to a file inside workspace/.",
        schema=WriteFileInput,
        handler=lambda a: write_file(filepath=a["filepath"], content=a["content"]),
        permission_level="SAFE"
    ),
    "move_file": ToolDefinition(
        name="move_file",
        description="Move a file inside workspace/.",
        schema=MoveFileInput,
        handler=lambda a: move_file(source=a["source"], destination=a["destination"]),
        permission_level="CONFIRM"
    ),
    "copy_file": ToolDefinition(
        name="copy_file",
        description="Copy a file inside workspace/.",
        schema=CopyFileInput,
        handler=lambda a: copy_file(source=a["source"], destination=a["destination"]),
        permission_level="SAFE"
    ),
    "delete_file": ToolDefinition(
        name="delete_file",
        description="Delete a file or folder inside workspace/. High-risk action.",
        schema=DeleteFileInput,
        handler=lambda a: _delete_file_handler(filepath=a["filepath"]),
        permission_level="DANGEROUS"
    ),

    # Office Documents
    "create_word": ToolDefinition(
        name="create_word",
        description="Create a formatted Word document (.docx) in files/word/.",
        schema=CreateWordInput,
        handler=lambda a: create_word(filename=a["filename"], title=a["title"], content=a["content"]),
        permission_level="SAFE"
    ),
    "create_excel": ToolDefinition(
        name="create_excel",
        description="Create an Excel spreadsheet (.xlsx) in files/excel/.",
        schema=CreateExcelInput,
        handler=lambda a: create_excel(filename=a["filename"], headers=a["headers"], rows=a.get("rows", [])),
        permission_level="SAFE"
    ),
    "create_powerpoint": ToolDefinition(
        name="create_powerpoint",
        description="Create a PowerPoint presentation (.pptx) in files/ppt/.",
        schema=CreatePowerPointInput,
        handler=lambda a: create_powerpoint(
            filename=a["filename"],
            slides=[s.model_dump() if hasattr(s, "model_dump") else s for s in a["slides"]]
        ),
        permission_level="SAFE"
    ),

    # Autonomous Coding Agent
    "create_coding_project": ToolDefinition(
        name="create_coding_project",
        description="Scaffold a project folder in workspace/, write source files, execute, and run tests.",
        schema=CreateCodingProjectInput,
        handler=lambda a: coding_agent.create_and_verify_project(
            project_name=a["project_name"],
            project_type=a.get("project_type", "python"),
            description=a["description"],
            files=a["files"],
            run_entrypoint=a.get("run_entrypoint", True)
        ),
        permission_level="SAFE"
    ),
    "run_project_code": ToolDefinition(
        name="run_project_code",
        description="Execute an allowlisted development command (python, pytest, node, npm) inside workspace/.",
        schema=RunProjectCodeInput,
        handler=lambda a: execute_sandboxed_command(
            command_str=a["command"],
            cwd=(WORKSPACE_DIR / a["cwd"]) if a.get("cwd") else WORKSPACE_DIR
        ),
        permission_level="SAFE"
    ),

    # Memory & System
    "remember": ToolDefinition(
        name="remember",
        description="Save user preference or note to persistent memory.",
        schema=RememberInput,
        handler=lambda a: {"success": True, "result": add_memory(a["key"], a["value"]), "error": None, "verification": {"verified": True, "details": "Saved to memory."}},
        permission_level="SAFE"
    ),
    "recall": ToolDefinition(
        name="recall",
        description="Recall personal memory context or user preferences.",
        schema=RecallInput,
        handler=lambda a: {"success": True, "result": get_relevant_memory(a.get("query", "")), "error": None, "verification": {"verified": True, "details": "Memory retrieved."}},
        permission_level="SAFE"
    ),
    "check_status": ToolDefinition(
        name="check_status",
        description="Check status of Ollama, models, tools count, and workspace.",
        schema=CheckStatusInput,
        handler=lambda a: _check_status_handler(detail=a.get("detail", False)),
        permission_level="SAFE"
    ),
}


def get_available_tools_schema() -> List[Dict[str, Any]]:
    """Returns Ollama/OpenAI tool definitions for all registered tools."""
    return [tool_def.to_ollama_tool() for tool_def in REGISTRY.values()]


TOOL_CATEGORIES = {
    "desktop": {
        "keywords": ["notepad", "calc", "calculator", "paint", "chrome", "edge", "vscode", "type", "press", "screenshot", "active window", "desktop", "application", "window"],
        "tools": ["open_application", "type_text", "press_key", "take_screenshot", "open_file"]
    },
    "word": {
        "keywords": ["word", "docx", "document", "doc", "essay", "report", "article"],
        "tools": ["create_word", "open_file", "list_files", "web_search"]
    },
    "excel": {
        "keywords": ["excel", "xlsx", "sheet", "spreadsheet", "table", "csv", "rows", "columns"],
        "tools": ["create_excel", "open_file", "list_files", "web_search"]
    },
    "ppt": {
        "keywords": ["powerpoint", "pptx", "ppt", "slide", "slides", "presentation"],
        "tools": ["create_powerpoint", "open_file", "list_files", "web_search"]
    },
    "search": {
        "keywords": ["search", "google", "find", "news", "lookup", "latest", "internet", "web", "who is", "what is", "current", "weather", "jobs", "mumbai"],
        "tools": ["web_search", "research_webpage", "browser_open", "browser_search"]
    },
    "browser": {
        "keywords": ["browser", "playwright", "extract", "click", "navigate", "page", "url", "website", "html"],
        "tools": ["browser_open", "browser_search", "browser_extract", "browser_screenshot", "web_search"]
    },
    "coding": {
        "keywords": ["code", "coding", "program", "python", "script", "test", "project", "develop", "app", "calculator", "function", "run code", "build"],
        "tools": ["create_coding_project", "run_project_code", "create_file", "read_file", "write_file", "list_files"]
    },
    "files": {
        "keywords": ["file", "files", "folder", "directory", "list", "read", "write", "delete", "move", "copy", "workspace", "text file"],
        "tools": ["list_files", "read_file", "create_file", "write_file", "delete_file", "open_file"]
    },
    "memory": {
        "keywords": ["remember", "memory", "prefer", "preference", "recall", "forget", "my name", "favorite"],
        "tools": ["remember", "recall"]
    },
}

DEFAULT_CORE_TOOLS = ["web_search", "open_application", "type_text", "create_file", "open_file", "remember", "recall"]


def select_relevant_tools(query: str, max_tools: int = 10) -> List[Dict[str, Any]]:
    """
    Selects a focused subset of tools matching the user's query context.
    Prevents token explosion and CPU latency with local Ollama models.
    """
    query_lower = query.lower()
    selected_tool_names = set()

    for category, config in TOOL_CATEGORIES.items():
        if any(kw in query_lower for kw in config["keywords"]):
            for t_name in config["tools"]:
                if t_name in REGISTRY:
                    selected_tool_names.add(t_name)

    # If no category matched or few tools selected, add default core tools
    if not selected_tool_names:
        for t_name in DEFAULT_CORE_TOOLS:
            if t_name in REGISTRY:
                selected_tool_names.add(t_name)

    # Convert to Ollama tool definitions, capped at max_tools
    selected_defs = []
    for t_name in list(selected_tool_names)[:max_tools]:
        selected_defs.append(REGISTRY[t_name].to_ollama_tool())

    return selected_defs



def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    timeout_seconds: int = TOOL_TIMEOUT_SECONDS,
    approval_callback: Optional[Callable[[Dict[str, Any]], bool]] = None
) -> Dict[str, Any]:
    """
    Validates tool and arguments via strict Pydantic model, checks approvals and security,
    and executes with a hard timeout limit.
    """
    logger.info(f"Tool execution requested: '{tool_name}' with args: {arguments}")

    # 1. Verify Tool Existence
    if tool_name not in REGISTRY:
        if tool_name in ("run_shell_command", "execute_command", "bash", "powershell"):
            logger.warning(f"Blocked arbitrary shell tool call: {tool_name}")
            return {
                "success": False,
                "result": None,
                "error": "Arbitrary shell/PowerShell command execution is strictly blocked for security.",
                "verification": {"verified": False, "details": "Blocked by policy."}
            }
        logger.warning(f"Unknown tool requested: {tool_name}")
        return {
            "success": False,
            "result": None,
            "error": f"Tool '{tool_name}' is not recognized. Valid tools: {', '.join(REGISTRY.keys())}",
            "verification": {"verified": False, "details": "Tool unknown."}
        }

    tool_def = REGISTRY[tool_name]

    # 2. Strict Pydantic Argument Validation
    try:
        validated_model = tool_def.schema(**arguments)
        validated_args = validated_model.model_dump()
    except ValidationError as ve:
        logger.error(f"Pydantic argument validation failed for '{tool_name}': {ve}")
        return {
            "success": False,
            "result": None,
            "error": f"Invalid arguments for tool '{tool_name}': {ve.errors()}",
            "verification": {"verified": False, "details": "Pydantic validation failed."}
        }

    # 3. Check for Approval Requirement
    if tool_def.requires_approval:
        reason = f"Action '{tool_name}' ({tool_def.permission_level}) requires explicit user approval."
        
        # If interactive approval callback provided (e.g. CLI), prompt directly
        if approval_callback:
            approved = approval_callback({
                "tool": tool_name,
                "arguments": validated_args,
                "reason": reason
            })
            if not approved:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Action '{tool_name}' was rejected by user.",
                    "verification": {"verified": False, "details": "User rejected approval."}
                }
        else:
            approval = create_pending_approval(
                tool=tool_name,
                arguments=validated_args,
                reason=reason
            )
            return {
                "status": "pending_approval",
                "approval_id": approval.id,
                "message": f"Action '{tool_name}' requires approval. Approval ID: {approval.id}",
                "pending_approval": approval.model_dump()
            }

    # 4. Execute with Timeout Guard
    def _run():
        return tool_def.handler(validated_args)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run)
            outcome = future.result(timeout=timeout_seconds)
            logger.info(f"Tool '{tool_name}' finished execution successfully.")

            # Standardize return format if handler returned dict
            if isinstance(outcome, dict) and "verification" in outcome:
                return outcome
            return {
                "success": True,
                "result": outcome,
                "error": None,
                "verification": {"verified": True, "details": f"Tool '{tool_name}' completed."}
            }

    except FutureTimeoutError:
        logger.error(f"Tool '{tool_name}' timed out after {timeout_seconds} seconds.")
        return {
            "success": False,
            "result": None,
            "error": f"Tool '{tool_name}' execution timed out after {timeout_seconds} seconds.",
            "verification": {"verified": False, "details": "Tool timed out."}
        }
    except SecurityViolationError as sve:
        logger.error(f"Security violation during tool '{tool_name}': {sve}")
        return {
            "success": False,
            "result": None,
            "error": f"Security violation: {str(sve)}",
            "verification": {"verified": False, "details": "Security constraint failed."}
        }
    except Exception as e:
        logger.error(f"Tool execution exception in '{tool_name}': {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Error executing tool '{tool_name}': {str(e)}",
            "verification": {"verified": False, "details": "Exception raised."}
        }
