from pathlib import Path

from app.infrastructure.repositories.thread_repository import SQLiteThreadRepository


DB_PATH = Path(__file__).resolve().parent.parent / "threads.db"
thread_repository = SQLiteThreadRepository(DB_PATH)


def init_db() -> None:
    thread_repository.init_db()


def create_thread(title: str = "New Chat") -> str:
    return thread_repository.create_thread(title=title)


def add_message(
    thread_id: str,
    role: str,
    content: str,
    sources: list[str] | None = None,
    source_items=None,
    needs_clarification: bool = False,
):
    thread_repository.add_message(
        thread_id,
        role,
        content,
        sources=sources,
        source_items=source_items,
        needs_clarification=needs_clarification,
    )


def get_threads():
    return [thread.model_dump() for thread in thread_repository.get_threads()]


def get_thread_messages(thread_id: str):
    return [message.model_dump() for message in thread_repository.get_thread_messages(thread_id)]
