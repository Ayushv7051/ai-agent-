"""
Telegram Integration Module for Ayush AI.
Enables Ayush to interact via Telegram when TELEGRAM_BOT_TOKEN is supplied.
Gracefully remains disabled if no token is provided.
"""

import threading
import time
import httpx
from typing import Optional
from config import TELEGRAM_BOT_TOKEN
from agent.orchestrator import orchestrator
from agent.logger import logger

_bot_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _run_telegram_polling(token: str) -> None:
    """Lightweight asynchronous-safe long-polling loop for Telegram updates."""
    base_url = f"https://api.telegram.org/bot{token}"
    last_update_id = 0
    logger.info("Starting Telegram Bot listener thread...")

    with httpx.Client(timeout=30) as client:
        while not _stop_event.is_set():
            try:
                url = f"{base_url}/getUpdates?offset={last_update_id + 1}&timeout=20"
                response = client.get(url)
                if response.status_code != 200:
                    time.sleep(5)
                    continue

                data = response.json()
                if not data.get("ok"):
                    time.sleep(5)
                    continue

                for update in data.get("result", []):
                    last_update_id = update.get("update_id", last_update_id)
                    message = update.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "")

                    if not chat_id or not text:
                        continue

                    if text.startswith("/start"):
                        welcome_msg = (
                            "Hello! I am Ayush AI, your personal assistant.\n"
                            "You can ask me questions, request web searches, or generate documents."
                        )
                        client.post(f"{base_url}/sendMessage", json={"chat_id": chat_id, "text": welcome_msg})
                        continue

                    # Forward to Agent Orchestrator
                    result = orchestrator.run(user_message=text)
                    reply_text = result.response
                    
                    client.post(f"{base_url}/sendMessage", json={"chat_id": chat_id, "text": reply_text})

            except Exception as e:
                logger.error(f"Telegram polling loop encountered error: {e}")
                time.sleep(5)


def init_telegram_bot() -> None:
    """Initializes and launches the Telegram bot in a background daemon thread if token exists."""
    global _bot_thread

    if not TELEGRAM_BOT_TOKEN:
        logger.info("Telegram integration disabled (TELEGRAM_BOT_TOKEN is not configured).")
        return

    logger.info("Configured TELEGRAM_BOT_TOKEN detected. Starting Telegram service...")
    _stop_event.clear()
    _bot_thread = threading.Thread(
        target=_run_telegram_polling,
        args=(TELEGRAM_BOT_TOKEN,),
        daemon=True,
        name="TelegramBotThread"
    )
    _bot_thread.start()


def stop_telegram_bot() -> None:
    """Signals the Telegram background worker to terminate."""
    if _bot_thread and _bot_thread.is_alive():
        _stop_event.set()
