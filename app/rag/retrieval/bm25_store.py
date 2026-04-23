import math
import re

from app.core.settings import settings
from app.domain.models import DocumentChunk, SourceItem

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover - optional dependency fallback
    BM25Okapi = None


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[ก-๙]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


class BM25Index:
    def __init__(self):
        self._index: dict[str, dict[str, object]] = {}

    def rebuild(self, chunks: list[DocumentChunk]) -> None:
        grouped: dict[str, list[DocumentChunk]] = {"__all__": list(chunks)}
        for chunk in chunks:
            grouped.setdefault(chunk.collection_id, []).append(chunk)

        self._index = {}
        for key, group_chunks in grouped.items():
            tokenized = [_tokenize(chunk.text) for chunk in group_chunks]
            engine = BM25Okapi(tokenized) if BM25Okapi and tokenized else None
            self._index[key] = {
                "chunks": group_chunks,
                "tokenized": tokenized,
                "engine": engine,
            }

    def search(
        self,
        query: str,
        *,
        collection_id: str | None = None,
        n_results: int = 3,
    ) -> list[SourceItem]:
        key = collection_id or "__all__"
        bucket = self._index.get(key)
        if not bucket:
            return []

        chunks: list[DocumentChunk] = bucket["chunks"]  # type: ignore[assignment]
        tokenized: list[list[str]] = bucket["tokenized"]  # type: ignore[assignment]
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores: list[float]
        if bucket["engine"] is not None:
            scores = list(bucket["engine"].get_scores(query_tokens))  # type: ignore[union-attr]
        else:
            query_terms = set(query_tokens)
            scores = []
            for tokens in tokenized:
                overlap = len(query_terms.intersection(tokens))
                denominator = math.sqrt(len(query_terms) * max(len(tokens), 1))
                scores.append(overlap / denominator if denominator else 0.0)

        ranked = sorted(zip(chunks, scores), key=lambda item: item[1], reverse=True)
        return [
            SourceItem(
                chunk_id=chunk.id,
                text=chunk.text,
                document=chunk.document,
                collection_id=chunk.collection_id,
                chapter=chunk.chapter,
                article=chunk.article,
                score=float(score),
                retrieval_method="bm25",
                citation=self._format_citation(chunk),
                chunk_index=int(chunk.metadata.get("chunk_index", 0)),
                metadata=chunk.metadata,
            )
            for chunk, score in ranked[:n_results]
            if score > 0
        ]

    @staticmethod
    def _format_citation(chunk: DocumentChunk) -> str | None:
        parts: list[str] = []
        if chunk.document:
            parts.append(str(chunk.document))
        if chunk.chapter:
            parts.append(f"บท {chunk.chapter}")
        if chunk.article:
            parts.append(f"มาตรา {chunk.article}")
        chunk_index = chunk.metadata.get("chunk_index")
        if chunk_index is not None:
            parts.append(f"chunk {chunk_index}")
        return " | ".join(parts) or None
