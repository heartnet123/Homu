from typing import Any

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    id: str
    text: str
    document: str
    collection_id: str
    chapter: str | None = None
    article: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceItem(BaseModel):
    chunk_id: str
    text: str
    document: str
    collection_id: str
    chapter: str | None = None
    article: str | None = None
    score: float | None = None
    retrieval_method: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def as_legacy_text(self) -> str:
        tags = [f"[Collection: {self.collection_id}]", f"[Doc: {self.document}]"]
        if self.chapter:
            tags.append(f"[Chapter: {self.chapter}]")
        if self.article:
            tags.append(f"[Article: {self.article}]")
        return " ".join(tags + [self.text])


class ClarificationResult(BaseModel):
    sufficient: bool
    clarification_question: str | None = None
    confidence: float | None = None
    raw_analysis: str


class SearchResult(BaseModel):
    strategy: str
    confidence: float
    sources: list[SourceItem] = Field(default_factory=list)
    expanded_to_all_collections: bool = False


class CollectionInfo(BaseModel):
    id: str
    name: str
    document_count: int = 0


class ThreadSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ThreadMessage(BaseModel):
    role: str
    content: str
    sources: list[str] = Field(default_factory=list)
    source_items: list[SourceItem] = Field(default_factory=list)
    needs_clarification: bool = False
    created_at: str
