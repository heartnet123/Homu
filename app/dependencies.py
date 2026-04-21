from functools import lru_cache
from pathlib import Path

from app.application.services.chat import (
    AskQuestionUseCase,
    LegalAssistantWorkflowService,
    StreamAnswerUseCase,
)
from app.application.services.documents import DocumentService, KnowledgeBaseService
from app.application.services.threads import ThreadService
from app.core.settings import settings
from app.database import DB_PATH, thread_repository
from app.graph.builder import build_legal_rag_graph
from app.infrastructure.document_loader import DocumentLoader
from app.infrastructure.llm_service import LLMService
from app.infrastructure.repositories.thread_repository import SQLiteThreadRepository
from app.infrastructure.vectorstores.chroma_store import ChromaVectorStore
from app.rag.retrieval.bm25_store import BM25Index
from app.rag.retrieval.hybrid import HybridRetriever


@lru_cache(maxsize=1)
def get_document_loader() -> DocumentLoader:
    return DocumentLoader(str(settings.resolved_doc_path))


@lru_cache(maxsize=1)
def get_document_service() -> DocumentService:
    return DocumentService(settings.resolved_doc_path)


@lru_cache(maxsize=1)
def get_vector_store() -> ChromaVectorStore:
    return ChromaVectorStore()


@lru_cache(maxsize=1)
def get_embedding_service() -> ChromaVectorStore:
    return get_vector_store()


@lru_cache(maxsize=1)
def get_bm25_index() -> BM25Index:
    return BM25Index()


@lru_cache(maxsize=1)
def get_knowledge_base_service() -> KnowledgeBaseService:
    return KnowledgeBaseService(
        document_loader=get_document_loader(),
        vector_store=get_vector_store(),
        bm25_index=get_bm25_index(),
    )


@lru_cache(maxsize=1)
def get_hybrid_retriever() -> HybridRetriever:
    return HybridRetriever(
        vector_store=get_vector_store(),
        bm25_index=get_bm25_index(),
    )


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService()


@lru_cache(maxsize=1)
def get_workflow_service() -> LegalAssistantWorkflowService:
    return LegalAssistantWorkflowService(
        knowledge_base_service=get_knowledge_base_service(),
        retriever=get_hybrid_retriever(),
        llm_service=get_llm_service(),
    )


@lru_cache(maxsize=1)
def get_thread_repository() -> SQLiteThreadRepository:
    return thread_repository


@lru_cache(maxsize=1)
def get_thread_service() -> ThreadService:
    return ThreadService(get_thread_repository())


@lru_cache(maxsize=1)
def get_legal_rag_graph():
    return build_legal_rag_graph(workflow_service=get_workflow_service())


@lru_cache(maxsize=1)
def get_ask_question_use_case() -> AskQuestionUseCase:
    return AskQuestionUseCase(
        graph=get_legal_rag_graph(),
        thread_repository=get_thread_repository(),
    )


@lru_cache(maxsize=1)
def get_stream_answer_use_case() -> StreamAnswerUseCase:
    return StreamAnswerUseCase(
        graph=get_legal_rag_graph(),
        thread_repository=get_thread_repository(),
    )


def get_capabilities_payload() -> dict:
    return {
        "models": get_llm_service().get_supported_models(),
        "search_strategies": ["vector", "bm25", "hybrid"],
        "default_model": settings.LLM_MODEL_NAME,
        "default_search_strategy": settings.DEFAULT_SEARCH_STRATEGY,
        "default_confidence_threshold": settings.DEFAULT_CONFIDENCE_THRESHOLD,
        "collections": [collection.model_dump() for collection in get_knowledge_base_service().get_collections()],
    }


__all__ = [
    "get_ask_question_use_case",
    "get_bm25_index",
    "get_capabilities_payload",
    "get_document_loader",
    "get_document_service",
    "get_embedding_service",
    "get_hybrid_retriever",
    "get_knowledge_base_service",
    "get_legal_rag_graph",
    "get_llm_service",
    "get_stream_answer_use_case",
    "get_thread_repository",
    "get_thread_service",
    "get_vector_store",
    "get_workflow_service",
]
