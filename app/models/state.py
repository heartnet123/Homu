from typing import Annotated, Any, TypedDict

from app.domain.models import ClarificationResult, SourceItem

try:
    from langchain_core.messages import BaseMessage
    from langgraph.graph.message import add_messages
except ImportError:  # pragma: no cover - fallback for environments without runtime deps
    BaseMessage = Any

    def add_messages(current, new):
        return (current or []) + (new or [])


class LegalRAGState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    query: str
    thread_id: str
    retrieved_docs: list[str]
    source_items: list[SourceItem]
    sources: list[str]
    analysis: str | None
    clarification_result: ClarificationResult | None
    answer: str | None
    iteration: int
    needs_clarification: bool
    model: str | None
    collection_id: str | None
    search_strategy: str | None
    confidence_threshold: float | None
    retrieval_confidence: float
    expanded_to_all_collections: bool
