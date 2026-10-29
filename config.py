"""
Central configuration for Ayush AI personal agent.
Loads environment variables and initializes core filesystem paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory: Points to project root dynamically
BASE_DIR = Path(__file__).resolve().parent

# Load .env file from BASE_DIR if present
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

# Storage and Sandbox Directories
DATA_DIR = BASE_DIR / "data"
FILES_DIR = BASE_DIR / "files"
WORD_DIR = FILES_DIR / "word"
EXCEL_DIR = FILES_DIR / "excel"
PPT_DIR = FILES_DIR / "ppt"
WORKSPACE_DIR = BASE_DIR / "workspace"
LOGS_DIR = BASE_DIR / "logs"

# Ensure all essential directories exist
for folder in [DATA_DIR, FILES_DIR, WORD_DIR, EXCEL_DIR, PPT_DIR, WORKSPACE_DIR, LOGS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Database & Persistent Files
DATABASE_PATH = DATA_DIR / "agent.db"
MEMORY_FILE = DATA_DIR / "memory.json"
LOG_FILE = LOGS_DIR / "agent.log"

# Ollama Settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
OLLAMA_NUM_THREADS = int(os.getenv("OLLAMA_NUM_THREADS", "8"))

# Web Server Settings
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# Telegram Bot Token (Optional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Computer Automation Allowlist
_allowed_apps_raw = os.getenv(
    "ALLOWED_APPLICATIONS",
    "notepad,calc,calculator,mspaint,paint,browser,chrome,edge,vscode,code"
)
ALLOWED_APPLICATIONS = [app.strip().lower() for app in _allowed_apps_raw.split(",") if app.strip()]

# Agent Loop & Timeout Limits
MAX_AGENT_ITERATIONS = int(os.getenv("MAX_AGENT_ITERATIONS", "8"))
TOOL_TIMEOUT_SECONDS = int(os.getenv("TOOL_TIMEOUT_SECONDS", "25"))
