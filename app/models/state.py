from typing import Annotated, Any, List, Optional, TypedDict

try:
    from langchain_core.messages import BaseMessage
    from langgraph.graph.message import add_messages
except ImportError:  # pragma: no cover - fallback for environments without runtime deps
    BaseMessage = Any

    def add_messages(current, new):
        return (current or []) + (new or [])


class LegalRAGState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    retrieved_docs: List[str]
    analysis: Optional[str]
    answer: Optional[str]
    sources: List[str]
    iteration: int
    needs_clarification: bool
    model: Optional[str]

