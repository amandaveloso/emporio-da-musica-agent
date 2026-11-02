"""Persistência leve de histórico de conversas em SQLite (local ou serverless /tmp)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import SESSIONS_DB_PATH


class ConversationMemory:
    """Armazena e recupera turnos de conversa por `session_id`."""

    def __init__(self, db_path: Path = SESSIONS_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_traces_json TEXT,
                model_used TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_session
                ON chat_messages(session_id, id);
            """
        )
        self.conn.commit()

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_traces: list[dict[str, Any]] | None = None,
        model_used: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, tool_traces_json, model_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                content,
                json.dumps(tool_traces, ensure_ascii=False) if tool_traces else None,
                model_used,
                now,
            ),
        )
        self.conn.commit()

    def get_history(self, session_id: str, limit: int = 16) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT role, content, tool_traces_json, model_used, created_at
            FROM (
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (session_id, limit),
        ).fetchall()

        history: list[dict[str, Any]] = []
        for r in rows:
            history.append(
                {
                    "role": r["role"],
                    "content": r["content"],
                    "tool_traces": (
                        json.loads(r["tool_traces_json"])
                        if r["tool_traces_json"]
                        else []
                    ),
                    "model_used": r["model_used"],
                    "created_at": r["created_at"],
                }
            )
        return history

    def clear_session(self, session_id: str) -> None:
        self.conn.execute(
            "DELETE FROM chat_messages WHERE session_id = ?", (session_id,)
        )
        self.conn.commit()


_memory_instance: ConversationMemory | None = None


def get_memory() -> ConversationMemory:
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ConversationMemory()
    return _memory_instance
