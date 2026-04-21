from functools import lru_cache

from app.config import settings
from app.graph.builder import build_legal_rag_graph
from app.services.document_loader import DocumentLoader
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService


@lru_cache(maxsize=1)
def get_document_loader() -> DocumentLoader:
    return DocumentLoader(str(settings.resolved_doc_path))


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService()


@lru_cache(maxsize=1)
def get_legal_rag_graph():
    return build_legal_rag_graph(
        embedding_service=get_embedding_service(),
        llm_service=get_llm_service(),
    )

