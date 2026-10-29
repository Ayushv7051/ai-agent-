# Ayush AI — Personal AI Agent for Windows (V1)

**Ayush AI** is a modular, local-first personal AI assistant built for Windows laptops. It operates locally using Ollama and the **Qwen3 8B** model, requires **zero paid APIs**, and integrates tools for web search, document generation (Word, Excel, PowerPoint), Playwright browser automation, safe computer control, persistent memory, and a real human-in-the-loop approval workflow.

---

## Key Features

1. **Local AI Engine**: Powered by `qwen3:8b` via local Ollama (`http://localhost:11434`).
2. **Interactive Web Dashboard**: Modern dark-mode interface with glassmorphism, dynamic tool activity streams, live Ollama status, and file download pills.
3. **Provider-Independent Web Search**: DuckDuckGo provider with modular architecture to plug in Bing, Google, or SearXNG later.
4. **Office Document Generation**:
   - **Word (`.docx`)**: Clean typography, headings, metadata, and bullet points.
   - **Excel (`.xlsx`)**: Auto-column sizing, frozen header row, styling, and zebra striping.
   - **PowerPoint (`.pptx`)**: Modern 16:9 widescreen presentation slides.
5. **Browser & Desktop Automation**:
   - **Playwright**: High-fidelity browser navigation and clean readable text extraction.
   - **PyAutoGUI**: Controlled desktop automation (keystrokes, screenshot, allowlisted apps).
6. **Real Approval & Safety System**:
   - Destructive actions generate a pending approval with a unique UUID.
   - Dashboard provides **Approve** and **Reject** buttons before any risky tool executes.
   - Strict path containment (`workspace/` and `files/` sandbox).
   - Sensitive Windows system directories (`C:\Windows`, `C:\System32`) and arbitrary shell commands are strictly blocked.
7. **Execution Guardrails**: Max 8 tool iterations per request with execution timeouts.
8. **Personal Persistent Memory**: Stores preferences and context in `data/memory.json`.
9. **SQLite Audit Trail**: Logs conversation turns and tool calls in `data/agent.db`.
10. **Future Coding Agent Scaffold**: Abstract base interfaces for V2 autonomous coding in `coding_agent/`.
11. **Decoupled Health API**: `/health` continues to report status even if Ollama is offline.
12. **Telegram Bridge**: Prepared for Telegram bot interaction via `TELEGRAM_BOT_TOKEN`.

---

## Project Structure

```text
C:\AI-Agent
│
├── main.py                     # FastAPI application & server lifecycle
├── config.py                   # Central settings & dynamic directory resolver
├── requirements.txt            # Pinned dependencies
├── .env                        # Active environment variables
├── .env.example                # Template environment variables
├── .gitignore                  # Git exclusions
├── README.md                   # Complete documentation
├── setup.bat                   # Automated Windows setup script
├── run.bat                     # Automated Windows launcher
│
├── agent/
│   ├── __init__.py
│   ├── brain.py                # Ollama client & structured reasoning
│   ├── orchestrator.py         # 8-turn tool loop & approval manager
│   ├── tools.py                # Pydantic-validated tool registry
│   ├── schemas.py              # Strict Pydantic models for tools & approvals
│   ├── permissions.py          # Path containment & approval lifecycles
│   ├── memory.py               # Persistent personal memory manager
│   ├── search.py               # Provider-independent web search & research
│   ├── browser.py              # Playwright browser automation
│   ├── computer.py             # PyAutoGUI desktop control (safe actions)
│   ├── documents.py            # Word document generator
│   ├── excel.py                # Excel spreadsheet generator
│   ├── powerpoint.py           # PowerPoint presentation generator
│   └── logger.py               # Secret-redacting rotating logger
│
├── coding_agent/               # V2 Module Scaffold (clean interfaces)
│   ├── __init__.py
│   ├── planner.py              # Coding planner interface
│   ├── workspace.py            # Workspace file management interface
│   ├── executor.py             # Sandbox executor interface
│   └── tester.py               # Automated tester interface
│
├── api/
│   ├── __init__.py
│   └── routes.py               # /chat, /health, /memory, /files, /approvals
│
├── database/
│   ├── __init__.py
│   └── db.py                   # SQLite persistence (data/agent.db)
│
├── telegram/
│   ├── __init__.py
│   └── bot.py                  # Optional Telegram bot background listener
│
├── frontend/
│   ├── index.html              # Modern dashboard UI
│   ├── style.css               # Glassmorphic dark styling
│   └── app.js                  # Frontend state & approval controller
│
├── data/
│   ├── memory.json             # Personal user preferences
│   └── agent.db                # SQLite database (auto-generated)
│
├── files/
│   ├── word/                   # Generated Word files
│   ├── excel/                  # Generated Excel files
│   └── ppt/                    # Generated PowerPoint presentations
│
├── workspace/                  # Scratch & screenshot sandbox
├── logs/
│   └── agent.log               # Application logs (auto-generated)
└── tests/
    ├── __init__.py
    ├── test_agent.py           # Core functionality test suite
    └── test_security.py        # Security, sandbox & approval test suite
```

---

## Prerequisites

- **OS**: Windows 10 or 11
- **Python**: 3.11.9 (or 3.11+)
- **Ollama**: Installed and running on `http://localhost:11434`
- **Model**: `qwen3:8b` pulled via:
  ```powershell
  ollama pull qwen3:8b
  ```

---

## Quick Setup (Windows)

### Option A: Automatic Script (Recommended)

Double-click or run:
```cmd
setup.bat
```
This script will:
1. Detect Python 3.11.
2. Create a virtual environment `.venv`.
3. Upgrade `pip` and install all dependencies in `requirements.txt`.
4. Install Playwright browser binaries (`playwright install chromium`).

### Option B: Manual Setup

1. Open PowerShell in the project directory:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   python -m playwright install chromium
   ```

---

## Starting the Application

### Option A: Automatic Launcher

Double-click or run:
```cmd
run.bat
```

### Option B: Manual Command

```powershell
.\.venv\Scripts\activate
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Accessing the Web Dashboard

Open your web browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## Running the Automated Test Suite

Ayush AI includes comprehensive unit and security tests. Run them using:

```powershell
# Run all tests
python -m unittest discover tests -v

# Run core functional tests only
python -m unittest tests/test_agent.py -v

# Run security and permissions tests only
python -m unittest tests/test_security.py -v
```

---

## How Tools & Approvals Work

### 1. Structured Invocation
Every tool uses a strict Pydantic model (`agent/schemas.py`). Ayush AI does not execute arbitrary natural-language commands. All tool names and parameters are validated before execution.

### 2. Human-in-the-Loop Approval System
When a high-risk tool is invoked (such as `delete_file` or system alteration):
1. The orchestrator pauses and generates a `PendingApproval` with a unique ID.
2. The web dashboard displays an **Approval Required** alert card showing tool details and reasons.
3. The user reviews the action and clicks **APPROVE** or **REJECT**.
4. The tool executes only upon explicit approval via `POST /approvals/{id}/approve`.

### 3. File Sandbox & Security Limitations
- All generated office files reside in `files/word/`, `files/excel/`, and `files/ppt/`.
- All screenshots and sandbox files reside in `workspace/`.
- Attempts to access or modify paths outside these folders or sensitive Windows directories (`C:\Windows`, `C:\System32`, `C:\Program Files`) are blocked by `validate_safe_path`.
- Arbitrary shell/PowerShell command execution is strictly blocked.
- Stock trading and financial transactions are intentionally excluded in V1.

---

## How to Add New Tools

To add a new capability:
1. Define a Pydantic input schema in `agent/schemas.py`:
   ```python
   class MyToolInput(BaseModel):
       param1: str = Field(..., description="Description")
   ```
2. Implement your tool handler function in `agent/`:
   ```python
   def my_handler(param1: str) -> dict:
       return {"success": True, "result": ...}
   ```
3. Register the tool in `agent/tools.py` in the `REGISTRY` map:
   ```python
   "my_tool": ToolDefinition(
       name="my_tool",
       description="Clear description for AI reasoning",
       schema=MyToolInput,
       handler=lambda args: my_handler(args["param1"]),
       requires_approval=False  # Set True if sensitive
   )
   ```
The AI brain will automatically detect the new tool and its schema on the next turn.

---

## Telegram Configuration (Optional)

1. Obtain a bot token from [@BotFather](https://t.me/botfather).
2. Edit `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
   ```
3. Start the server (`run.bat`). Ayush AI will launch a background polling worker and respond to your messages on Telegram. If left blank, Telegram is disabled without error.
