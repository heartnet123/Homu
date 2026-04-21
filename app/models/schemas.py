from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models import SourceItem


class LegalQueryRequest(BaseModel):
    query: str
    thread_id: str | None = None
    model: str | None = None
    collection_id: str | None = None
    search_strategy: Literal["vector", "bm25", "hybrid"] | None = None
    confidence_threshold: float | None = None


class LegalQueryResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    source_items: list[SourceItem] = Field(default_factory=list)
    analysis: str | None = None
    confidence: float | None = None
    thread_id: str | None = None
    needs_clarification: bool = False
    collection_id: str | None = None
    expanded_to_all_collections: bool = False
