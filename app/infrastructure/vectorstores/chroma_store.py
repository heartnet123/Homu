import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

from app.core.settings import settings
from app.domain.models import DocumentChunk, SourceItem


class ThaiLegalEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    @staticmethod
    def _as_embedding_matrix(vectors) -> list[list[float]]:
        values = vectors.tolist() if hasattr(vectors, "tolist") else vectors
        if not values:
            return []
        first = values[0]
        if isinstance(first, (int, float)):
            return [[float(value) for value in values]]
        return [[float(value) for value in vector] for vector in values]

    def __call__(self, input: Documents) -> Embeddings:
        texts: list[str] = []
        for item in input:
            if isinstance(item, list):
                texts.extend(item)
            else:
                texts.append(item)
        return self._as_embedding_matrix(self.model.encode(texts, show_progress_bar=False))

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        return self.__call__(documents)

    def embed_query(self, query: str | None = None, **kwargs) -> list[float]:
        text = query or kwargs.get("input") or kwargs.get("text")
        if text is None:
            raise ValueError("No text provided for embedding.")
        return self.__call__([text])[0]

    @staticmethod
    def name() -> str:
        return "thai-legal-embedding"


class ChromaVectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
        self.embedding_fn = ThaiLegalEmbeddingFunction(settings.EMBED_MODEL_NAME)
        self.collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
        )

    @staticmethod
    def _build_metadata(chunk: DocumentChunk) -> dict[str, str | float | int]:
        return {
            "document": chunk.document,
            "collection_id": chunk.collection_id,
            "chapter": chunk.chapter or "",
            "article": chunk.article or "",
            "source_path": str(chunk.metadata.get("source_path", "")),
            "source_mtime": float(chunk.metadata.get("source_mtime", 0.0)),
            "source_hash": str(chunk.metadata.get("source_hash", "")),
            "embedding_model": str(chunk.metadata.get("embedding_model", settings.EMBED_MODEL_NAME)),
            "pipeline_version": str(
                chunk.metadata.get("pipeline_version", settings.VECTOR_PIPELINE_VERSION)
            ),
            "chunk_index": int(chunk.metadata.get("chunk_index", 0)),
            "citation": str(chunk.metadata.get("citation", "")),
        }

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0

        self.collection.upsert(
            documents=[chunk.text for chunk in chunks],
            metadatas=[self._build_metadata(chunk) for chunk in chunks],
            ids=[chunk.id for chunk in chunks],
        )
        return len(chunks)

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        if not chunk_ids:
            return 0
        self.collection.delete(ids=chunk_ids)
        return len(chunk_ids)

    def delete_chunks_by_source(self, source_path: str) -> int:
        results = self.collection.get(where={"source_path": source_path}, include=[])
        chunk_ids = results.get("ids", [])
        if not chunk_ids:
            return 0
        self.collection.delete(ids=chunk_ids)
        return len(chunk_ids)

    def rebuild(self, chunks: list[DocumentChunk]) -> None:
        existing = self.collection.get(include=[])
        existing_ids = existing.get("ids", [])
        if existing_ids:
            self.collection.delete(ids=existing_ids)
        self.upsert_chunks(chunks)

    def count(self) -> int:
        return self.collection.count()

    def search(
        self,
        query: str,
        *,
        collection_id: str | None = None,
        n_results: int = 3,
    ) -> list[SourceItem]:
        if self.count() == 0:
            return []

        kwargs = {"query_embeddings": self._query_embeddings(query), "n_results": n_results}
        if collection_id:
            kwargs["where"] = {"collection_id": collection_id}

        results = self.collection.query(**kwargs)
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]

        items: list[SourceItem] = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            metadata = metadata or {}
            items.append(
                SourceItem(
                    chunk_id=chunk_id,
                    text=text,
                    document=metadata.get("document", ""),
                    collection_id=metadata.get("collection_id", settings.DEFAULT_COLLECTION_ID),
                    chapter=metadata.get("chapter") or None,
                    article=metadata.get("article") or None,
                    score=1.0 / (1.0 + float(distance)),
                    retrieval_method="vector",
                    citation=self._format_citation(metadata),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    metadata=metadata,
                )
            )
        return items

    def _query_embeddings(self, query: str) -> list[list[float]]:
        return ThaiLegalEmbeddingFunction._as_embedding_matrix(self.embedding_fn([query]))

    @staticmethod
    def _format_citation(metadata: dict[str, str | float | int]) -> str | None:
        parts: list[str] = []
        document = metadata.get("document")
        chapter = metadata.get("chapter")
        article = metadata.get("article")
        chunk_index = metadata.get("chunk_index")
        if document:
            parts.append(str(document))
        if chapter:
            parts.append(f"บท {chapter}")
        if article:
            parts.append(f"มาตรา {article}")
        if chunk_index is not None:
            parts.append(f"chunk {chunk_index}")
        return " | ".join(parts) or None
