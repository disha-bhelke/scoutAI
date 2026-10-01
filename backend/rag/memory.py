import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class ConversationMemory:
    """
    Lightweight, persistent SQLite-backed conversation memory store.
    Stores messages per conversation_id and formats chat history for LLM prompting.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent / "data"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "conversations.db"

        self._init_db()

    def _init_db(self):
        """Initializes the database schema if it doesn't already exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_id ON messages (conversation_id)
            """)
            conn.commit()

    def get_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Retrieves the last `limit` messages for the given conversation_id,
        ordered chronologically.
        """
        if not conversation_id:
            return []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content FROM (
                    SELECT id, role, content FROM messages
                    WHERE conversation_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                ) ORDER BY id ASC
                """,
                (conversation_id, limit)
            )
            rows = cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in rows]

    def add_message(self, conversation_id: str, role: str, content: str):
        """Adds a single message to the conversation."""
        if not conversation_id or not content:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content)
            )
            conn.commit()

    def format_history_for_prompt(self, conversation_id: str, limit: int = 10) -> str:
        """
        Formats previous messages as a clean text dialog block for the LLM prompt.
        """
        history = self.get_history(conversation_id, limit=limit)
        if not history:
            return "No previous conversation history."

        lines = []
        for msg in history:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)

    def delete_conversation(self, conversation_id: str):
        """Deletes all messages for a given conversation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.commit()
