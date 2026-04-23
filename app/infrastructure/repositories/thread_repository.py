from contextlib import closing
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.domain.models import SourceItem, ThreadMessage, ThreadSummary


class SQLiteThreadRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    @staticmethod
    def _utcnow() -> str:
        return datetime.now(UTC).isoformat()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _get_column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in rows}

    def _migrate_messages_table(self, conn: sqlite3.Connection) -> None:
        existing_columns = self._get_column_names(conn, "messages")
        if "source_items" not in existing_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN source_items TEXT")

    def init_db(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT,
                    role TEXT,
                    content TEXT,
                    sources TEXT,
                    source_items TEXT,
                    needs_clarification BOOLEAN,
                    created_at TEXT,
                    FOREIGN KEY (thread_id) REFERENCES threads (id)
                )
                """
            )
            self._migrate_messages_table(conn)
            conn.commit()

    def create_thread(self, title: str = "New Chat") -> str:
        thread_id = str(uuid.uuid4())
        now = self._utcnow()
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (thread_id, title, now, now),
            )
            conn.commit()
        return thread_id

    def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        sources: list[str] | None = None,
        source_items: list[SourceItem] | None = None,
        needs_clarification: bool = False,
    ) -> None:
        now = self._utcnow()
        sources_json = json.dumps(sources or [], ensure_ascii=False)
        source_items_json = json.dumps(
            [item.model_dump() for item in (source_items or [])],
            ensure_ascii=False,
        )
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO messages (thread_id, role, content, sources, source_items, needs_clarification, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    role,
                    content,
                    sources_json,
                    source_items_json,
                    needs_clarification,
                    now,
                ),
            )
            conn.execute("UPDATE threads SET updated_at = ? WHERE id = ?", (now, thread_id))
            conn.commit()

    def get_threads(self) -> list[ThreadSummary]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, title, created_at, updated_at FROM threads ORDER BY updated_at DESC"
            ).fetchall()
        return [ThreadSummary(**dict(row)) for row in rows]

    def get_thread_messages(self, thread_id: str) -> list[ThreadMessage]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT role, content, sources, source_items, needs_clarification, created_at
                FROM messages
                WHERE thread_id = ?
                ORDER BY id ASC
                """,
                (thread_id,),
            ).fetchall()

        messages: list[ThreadMessage] = []
        for row in rows:
            payload = dict(row)
            source_items_raw = json.loads(payload["source_items"] or "[]")
            messages.append(
                ThreadMessage(
                    role=payload["role"],
                    content=payload["content"],
                    sources=json.loads(payload["sources"] or "[]"),
                    source_items=[SourceItem(**item) for item in source_items_raw],
                    needs_clarification=bool(payload["needs_clarification"]),
                    created_at=payload["created_at"],
                )
            )
        return messages
