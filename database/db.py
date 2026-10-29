"""
SQLite Database Module for Ayush AI.
Persists conversation histories, tool execution audits, and approval lifecycle states.
Database path: data/agent.db
"""

import sqlite3
import json
import datetime
from typing import List, Dict, Any, Optional
from config import DATABASE_PATH
from agent.logger import logger


def get_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Creates database tables automatically on startup."""
    logger.info(f"Initializing SQLite database at {DATABASE_PATH}")
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Conversations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tool Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                tool_name TEXT NOT NULL,
                arguments TEXT,
                status TEXT,
                result TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Approvals Audit Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                tool TEXT NOT NULL,
                arguments TEXT,
                reason TEXT,
                status TEXT NOT NULL,
                created_at DATETIME,
                resolved_at DATETIME
            )
        """)

        conn.commit()
    logger.info("SQLite database tables initialized successfully.")


def save_message(session_id: str, role: str, content: str) -> None:
    """Records a conversation turn."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error saving message to database: {e}")


def get_recent_messages(session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieves recent conversation messages for a session in chronological order."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content, timestamp 
                FROM conversations 
                WHERE session_id = ? 
                ORDER BY id DESC 
                LIMIT ?
                """,
                (session_id, limit)
            )
            rows = cursor.fetchall()
            messages = [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in rows]
            messages.reverse()
            return messages
    except Exception as e:
        logger.error(f"Error reading conversation history: {e}")
        return []


def log_tool_execution(
    session_id: Optional[str],
    tool_name: str,
    arguments: Dict[str, Any],
    status: str,
    result: Any
) -> None:
    """Logs tool execution outcomes to SQLite audit trail."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tool_logs (session_id, tool_name, arguments, status, result)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id or "default",
                    tool_name,
                    json.dumps(arguments, default=str),
                    status,
                    json.dumps(result, default=str) if not isinstance(result, str) else result
                )
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error logging tool execution to db: {e}")
