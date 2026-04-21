from app.domain.models import ThreadMessage, ThreadSummary


class ThreadService:
    def __init__(self, repository):
        self.repository = repository

    def create_thread(self, title: str = "New Chat") -> str:
        return self.repository.create_thread(title=title)

    def list_threads(self) -> list[ThreadSummary]:
        return self.repository.get_threads()

    def get_thread_messages(self, thread_id: str) -> list[ThreadMessage]:
        return self.repository.get_thread_messages(thread_id)
