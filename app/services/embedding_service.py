import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from app.config import settings


class ThaiLegalEmbeddingFunction(EmbeddingFunction[Documents]):
    """Custom embedding function for ChromaDB."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def __call__(self, input: Documents) -> Embeddings:
        # Debugging
        print(f"DEBUG: Embedding input type: {type(input)}, len: {len(input)}")
        if len(input) > 0:
            print(f"DEBUG: First item type: {type(input[0])}")

        # Flatten if ChromaDB passes nested lists
        texts = []
        for item in input:
            if isinstance(item, list):
                texts.extend(item)
            else:
                texts.append(item)
                
        print(f"DEBUG: Flattened texts len: {len(texts)}")
        embeddings = self.model.encode(texts, show_progress_bar=False)
        print(f"DEBUG: Embeddings type: {type(embeddings)}, shape: {getattr(embeddings, 'shape', 'N/A')}")
        
        result = embeddings.tolist()
        print(f"DEBUG: Result type: {type(result)}, len: {len(result)}")
        if len(result) > 0:
            print(f"DEBUG: First result element type: {type(result[0])}")
            if isinstance(result[0], list) and len(result[0]) > 0:
                print(f"DEBUG: First vector first element type: {type(result[0][0])}")
        
        return result

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        return self.__call__(documents)

    def embed_query(self, query: str = None, **kwargs) -> list[float]:
        text = query or kwargs.get("input") or kwargs.get("text")
        if text is None:
            raise ValueError("No text provided for embedding")
        return self.__call__([text])[0]

    @staticmethod
    def name() -> str:
        return "default"


class EmbeddingService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
        self.embedding_fn = ThaiLegalEmbeddingFunction(settings.EMBED_MODEL_NAME)
        self.collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
        )

    def reset_collection(self) -> None:
        self.client.delete_collection(name=settings.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
        )

    def initialize_collection(self, documents: list[dict], force: bool = False) -> None:
        if force:
            self.reset_collection()
        elif self.collection.count() > 0:
            return

        if not documents:
            return

        texts = [doc["text"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]
        ids = [f"doc_{index}" for index in range(len(documents))]
        self.collection.add(documents=texts, metadatas=metadatas, ids=ids)

    def search(self, query: str, n_results: int = 3) -> list[str]:
        results = self.collection.query(query_texts=[query], n_results=n_results)
        documents = results.get("documents", [[]])
        return documents[0] if documents else []
