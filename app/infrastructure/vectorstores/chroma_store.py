import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

from app.core.logging import logger
from app.core.settings import settings
from app.domain.models import DocumentChunk, SourceItem


class ThaiLegalEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def __call__(self, input: Documents) -> Embeddings:
        texts: list[str] = []
        for item in input:
            if isinstance(item, list):
                texts.extend(item)
            else:
                texts.append(item)
        return self.model.encode(texts, show_progress_bar=False).tolist()

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

    def rebuild(self, chunks: list[DocumentChunk]) -> None:
        try:
            self.client.delete_collection(name=settings.COLLECTION_NAME)
        except Exception:
            logger.debug("Collection %s did not exist before rebuild.", settings.COLLECTION_NAME)

        self.collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
        )

        if not chunks:
            return

        documents = [chunk.text for chunk in chunks]
        metadatas = []
        ids = []
        for chunk in chunks:
            ids.append(chunk.id)
            metadatas.append(
                {
                    "document": chunk.document,
                    "collection_id": chunk.collection_id,
                    "chapter": chunk.chapter or "",
                    "article": chunk.article or "",
                    "source_path": str(chunk.metadata.get("source_path", "")),
                }
            )

        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)

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

        kwargs = {"query_texts": [query], "n_results": n_results}
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
                    metadata=metadata,
                )
            )
        return items
