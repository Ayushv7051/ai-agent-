"""
Strict Pydantic schemas for all tools, parameters, approvals, and API payloads.
Ensures no unstructured execution happens anywhere in Ayush AI.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Web & Research Schemas
# ---------------------------------------------------------

class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query or keywords")
    max_results: int = Field(5, ge=1, le=20, description="Maximum search results (1-20)")


class ResearchWebpageInput(BaseModel):
    url: str = Field(..., description="URL of webpage to research and summarize")


class OpenUrlInput(BaseModel):
    url: str = Field(..., description="Web URL to open in the browser")


# ---------------------------------------------------------
# Browser Automation (Playwright) Schemas
# ---------------------------------------------------------

class BrowserOpenInput(BaseModel):
    url: str = Field(..., description="URL to open in Playwright browser")
    headless: bool = Field(False, description="False to display real browser window on screen")


class BrowserSearchInput(BaseModel):
    query: str = Field(..., description="Search query to submit through browser")


class BrowserClickInput(BaseModel):
    selector: str = Field(..., description="CSS or text selector to click on webpage")
    url: Optional[str] = Field(None, description="Optional page URL to navigate to first")


class BrowserTypeInput(BaseModel):
    selector: str = Field(..., description="CSS selector for input field")
    text: str = Field(..., description="Text string to type into input field")


class BrowserExtractInput(BaseModel):
    url: str = Field(..., description="Web page URL to extract content from")
    selector: Optional[str] = Field(None, description="Optional CSS selector to extract specific container")


class BrowserScreenshotInput(BaseModel):
    url: str = Field(..., description="Web page URL to screenshot")
    filename: Optional[str] = Field(None, description="Optional output PNG filename in workspace/")


# ---------------------------------------------------------
# Computer Control (Desktop) Schemas
# ---------------------------------------------------------

class OpenApplicationInput(BaseModel):
    application: str = Field(..., description="Name of allowlisted application (notepad, calc, paint, chrome, edge, vscode)")


class OpenFileInput(BaseModel):
    filepath: str = Field(..., description="Path of file to open in default Windows app (e.g. Word, Excel, PowerPoint)")


class TypeTextInput(BaseModel):
    text: str = Field(..., description="Text to type via keyboard simulation into active window")


class PressKeyInput(BaseModel):
    key: str = Field(..., description="Key to press (enter, esc, tab, space, etc.)")


class TakeScreenshotInput(BaseModel):
    filename: Optional[str] = Field(None, description="Optional output filename in workspace/")


# ---------------------------------------------------------
# Filesystem Schemas (workspace/ and files/ sandbox)
# ---------------------------------------------------------

class ListFilesInput(BaseModel):
    directory: Optional[str] = Field(None, description="Subdirectory inside workspace/ or files/ to list")


class ReadFileInput(BaseModel):
    filepath: str = Field(..., description="Relative or absolute path of file inside sandbox to read")


class CreateFileInput(BaseModel):
    filepath: str = Field(..., description="Path of file to create inside workspace/")
    content: str = Field("", description="Initial text content of the file")


class WriteFileInput(BaseModel):
    filepath: str = Field(..., description="Path of file to write/overwrite inside workspace/")
    content: str = Field(..., description="Text content to write into file")


class MoveFileInput(BaseModel):
    source: str = Field(..., description="Source path inside workspace/")
    destination: str = Field(..., description="Destination path inside workspace/")


class CopyFileInput(BaseModel):
    source: str = Field(..., description="Source path inside workspace/")
    destination: str = Field(..., description="Destination path inside workspace/")


class DeleteFileInput(BaseModel):
    filepath: str = Field(..., description="Path to delete inside workspace/ (Requires explicit human approval)")


# ---------------------------------------------------------
# Office Documents Schemas
# ---------------------------------------------------------

class CreateWordInput(BaseModel):
    filename: str = Field(..., description="Name of Word file (e.g. report.docx)")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Body content with markdown headings and bullet points")


class CreateExcelInput(BaseModel):
    filename: str = Field(..., description="Name of Excel file (e.g. data.xlsx)")
    headers: List[str] = Field(..., min_length=1, description="Column headers")
    rows: List[List[Any]] = Field(default_factory=list, description="Row data matching headers")


class SlideItem(BaseModel):
    title: str = Field(..., description="Slide title")
    content: str = Field(..., description="Slide bullet points or body text")


class CreatePowerPointInput(BaseModel):
    filename: str = Field(..., description="Name of presentation (e.g. deck.pptx)")
    slides: List[SlideItem] = Field(..., min_length=1, description="List of slides")


# ---------------------------------------------------------
# Coding Agent Schemas
# ---------------------------------------------------------

class CreateCodingProjectInput(BaseModel):
    project_name: str = Field(..., description="Name of project folder inside workspace/")
    project_type: str = Field("python", description="Project type: python, javascript, html, react")
    description: str = Field(..., description="Goal and requirements of application")
    files: Dict[str, str] = Field(..., description="Dictionary mapping relative filenames to code contents")
    run_entrypoint: bool = Field(True, description="Whether to execute the entrypoint immediately after creation")


class RunProjectCodeInput(BaseModel):
    command: str = Field(..., description="Allowlisted command (python, pytest, npm, node) to run")
    cwd: Optional[str] = Field(None, description="Subdirectory inside workspace/ to run within")


# ---------------------------------------------------------
# Memory & System Schemas
# ---------------------------------------------------------

class RememberInput(BaseModel):
    key: str = Field(..., description="Preference category or note topic")
    value: str = Field(..., description="Information or preference to remember")


# Alias for backward compatibility with API routes
SaveMemoryInput = RememberInput


class RecallInput(BaseModel):
    query: Optional[str] = Field("", description="Keyword to recall from memory")


class CheckStatusInput(BaseModel):
    detail: Optional[bool] = Field(False, description="Whether to include full system diagnostics")


# ---------------------------------------------------------
# Tool Invocation & Approval Schemas
# ---------------------------------------------------------

class ToolInvocation(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class PendingApproval(BaseModel):
    id: str
    tool: str
    arguments: Dict[str, Any]
    reason: str
    status: Literal["pending", "approved", "rejected", "expired"] = "pending"
    created_at: str


class ToolActivity(BaseModel):
    tool: str
    action: str
    status: Literal["running", "success", "error", "pending_approval", "skipped"]
    details: Optional[str] = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    tool_activities: List[ToolActivity] = Field(default_factory=list)
    pending_approval: Optional[PendingApproval] = None
