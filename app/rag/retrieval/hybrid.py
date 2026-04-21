from collections.abc import Iterable

from app.core.logging import logger
from app.core.settings import settings
from app.domain.models import SearchResult, SourceItem


class _OptionalReranker:
    def __init__(self):
        self._model = None
        self._enabled = settings.ENABLE_RERANKER

    def rerank(self, query: str, sources: list[SourceItem]) -> list[SourceItem]:
        if not self._enabled or not sources:
            return sources

        try:
            if self._model is None:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(settings.RERANK_MODEL_NAME)

            pairs = [[query, source.text] for source in sources]
            scores = self._model.predict(pairs)
        except Exception:  # pragma: no cover - optional runtime path
            logger.exception("Reranker failed. Falling back to hybrid ordering.")
            return sources

        reranked = []
        for source, score in zip(sources, scores):
            reranked.append(source.model_copy(update={"score": float(score), "retrieval_method": "hybrid-reranked"}))
        return sorted(reranked, key=lambda item: item.score or 0.0, reverse=True)


class HybridRetriever:
    def __init__(self, vector_store, bm25_index):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.reranker = _OptionalReranker()

    @staticmethod
    def _rrf_merge(result_sets: Iterable[list[SourceItem]], limit: int) -> list[SourceItem]:
        scores: dict[str, float] = {}
        items: dict[str, SourceItem] = {}
        for result_set in result_sets:
            for rank, item in enumerate(result_set, start=1):
                scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1.0 / (60 + rank)
                items[item.chunk_id] = item

        merged = [
            items[chunk_id].model_copy(update={"score": score, "retrieval_method": "hybrid"})
            for chunk_id, score in scores.items()
        ]
        merged.sort(key=lambda item: item.score or 0.0, reverse=True)
        return merged[:limit]

    @staticmethod
    def _confidence(sources: list[SourceItem]) -> float:
        if not sources:
            return 0.0
        top_score = sources[0].score or 0.0
        if len(sources) == 1:
            return min(1.0, top_score)
        second_score = sources[1].score or 0.0
        return max(0.0, min(1.0, top_score - (second_score * 0.5) + 0.25))

    async def search(
        self,
        query: str,
        *,
        collection_id: str | None,
        strategy: str | None,
        n_results: int,
        confidence_threshold: float,
    ) -> SearchResult:
        normalized_strategy = (strategy or settings.DEFAULT_SEARCH_STRATEGY).lower()
        if normalized_strategy not in {"vector", "bm25", "hybrid"}:
            normalized_strategy = settings.DEFAULT_SEARCH_STRATEGY

        search_limit = max(n_results * 2, n_results)
        result = self._search_once(
            query,
            collection_id=collection_id,
            strategy=normalized_strategy,
            n_results=search_limit,
        )

        expanded = False
        if collection_id and result.confidence < confidence_threshold:
            fallback = self._search_once(
                query,
                collection_id=None,
                strategy=normalized_strategy,
                n_results=search_limit,
            )
            if fallback.confidence >= result.confidence:
                result = fallback
                expanded = True

        sources = result.sources[:n_results]
        if normalized_strategy == "hybrid":
            sources = self.reranker.rerank(query, sources)[:n_results]

        return SearchResult(
            strategy=normalized_strategy,
            confidence=self._confidence(sources),
            sources=sources,
            expanded_to_all_collections=expanded,
        )

    def _search_once(
        self,
        query: str,
        *,
        collection_id: str | None,
        strategy: str,
        n_results: int,
    ) -> SearchResult:
        if strategy == "vector":
            sources = self.vector_store.search(query, collection_id=collection_id, n_results=n_results)
        elif strategy == "bm25":
            sources = self.bm25_index.search(query, collection_id=collection_id, n_results=n_results)
        else:
            vector_sources = self.vector_store.search(query, collection_id=collection_id, n_results=n_results)
            bm25_sources = self.bm25_index.search(query, collection_id=collection_id, n_results=n_results)
            sources = self._rrf_merge([vector_sources, bm25_sources], limit=n_results)

        return SearchResult(
            strategy=strategy,
            confidence=self._confidence(sources),
            sources=sources,
            expanded_to_all_collections=False,
        )
