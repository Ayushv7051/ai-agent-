"""
Main Entrypoint for Ayush AI Application.
Sets up FastAPI server, static routes, database lifecycle, and Telegram bot.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import (
    BASE_DIR,
    SERVER_HOST,
    SERVER_PORT,
    WORD_DIR,
    EXCEL_DIR,
    PPT_DIR,
    WORKSPACE_DIR
)
from database.db import init_db
from agent.brain import check_ollama
from agent.logger import logger
from telegram.bot import init_telegram_bot, stop_telegram_bot
from api.routes import router as api_router

FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: initialize SQLite, inspect Ollama, start background services."""
    logger.info("==================================================")
    logger.info("Starting Ayush AI Agent Server (V1)")
    logger.info("==================================================")

    # 1. Initialize SQLite Database
    init_db()

    # 2. Check Ollama Connectivity
    ollama_ok, ollama_msg, _ = check_ollama()
    if ollama_ok:
        logger.info(f"Ollama Status: {ollama_msg}")
    else:
        logger.warning(f"Ollama Warning: {ollama_msg}")

    # 3. Start Telegram Integration (if configured)
    init_telegram_bot()

    yield

    # Clean shutdown
    logger.info("Shutting down Ayush AI services...")
    stop_telegram_bot()
    logger.info("Ayush AI shutdown complete.")


app = FastAPI(
    title="Ayush AI",
    description="Personal AI Agent for Windows with Local Ollama, Tools, and Safety Controls",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

# Mount Static File Directories for Downloads and Frontend
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
app.mount("/files/word", StaticFiles(directory=str(WORD_DIR)), name="word_files")
app.mount("/files/excel", StaticFiles(directory=str(EXCEL_DIR)), name="excel_files")
app.mount("/files/ppt", StaticFiles(directory=str(PPT_DIR)), name="ppt_files")
app.mount("/workspace/file", StaticFiles(directory=str(WORKSPACE_DIR)), name="workspace_files")


@app.get("/")
def serve_index():
    """Serves the main web dashboard."""
    index_path = FRONTEND_DIR / "index.html"
    return FileResponse(str(index_path))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
