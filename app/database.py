import sqlite3
import json
import uuid
import os
from datetime import datetime

# Place the database file in the project roor
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "threads.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT,
                role TEXT,
                content TEXT,
                sources TEXT,
                needs_clarification BOOLEAN,
                created_at TEXT,
                FOREIGN KEY (thread_id) REFERENCES threads (id)
            )
        """)
        conn.commit()

def create_thread(title: str = "New Chat") -> str:
    thread_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)", (thread_id, title, now, now))
        conn.commit()
    return thread_id

def add_message(thread_id: str, role: str, content: str, sources: list = None, needs_clarification: bool = False):
    now = datetime.utcnow().isoformat()
    sources_json = json.dumps(sources) if sources else None
    
    # Ensure thread exists and update its timestamp
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (thread_id, role, content, sources, needs_clarification, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (thread_id, role, content, sources_json, needs_clarification, now)
        )
        conn.execute("UPDATE threads SET updated_at = ? WHERE id = ?", (now, thread_id))
        conn.commit()

def get_threads():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT id, title, created_at, updated_at FROM threads ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_thread_messages(thread_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT role, content, sources, needs_clarification, created_at FROM messages WHERE thread_id = ? ORDER BY id ASC", (thread_id,))
        messages = []
        for row in cursor.fetchall():
            m = dict(row)
            if m["sources"]:
                m["sources"] = json.loads(m["sources"])
            messages.append(m)
        return messages
