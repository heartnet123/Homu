from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from app.config import settings
from app.dependencies import (
    get_document_loader,
    get_embedding_service,
    get_legal_rag_graph,
)
from app.models.schemas import LegalQueryRequest, LegalQueryResponse


def _create_human_message(content: str):
    from langchain_core.messages import HumanMessage

    return HumanMessage(content=content)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTO_INIT_COLLECTION:
        loader = get_document_loader()
        embed_service = get_embedding_service()
        documents = loader.load()
        embed_service.initialize_collection(documents)
        app.state.loaded_chunks = len(documents)
    yield


app = FastAPI(
    title="Thai Legal RAG API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post(f"{settings.API_V1_PREFIX}/ask", response_model=LegalQueryResponse)
async def ask_question(
    request: LegalQueryRequest,
    legal_rag_graph=Depends(get_legal_rag_graph),
):
    try:
        initial_state = {
            "messages": [_create_human_message(request.query)],
            "query": request.query,
            "retrieved_docs": [],
            "analysis": None,
            "answer": None,
            "sources": [],
            "iteration": 0,
            "needs_clarification": False,
        }

        result = legal_rag_graph.invoke(initial_state)

        return LegalQueryResponse(
            answer=result["answer"],
            sources=result.get("sources", [])[: settings.TOP_K_RESULTS],
            analysis=result.get("analysis"),
        )
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": settings.LLM_MODEL_NAME}

