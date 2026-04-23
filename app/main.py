from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.errors import AppError
from app.core.logging import logger
from app.core.settings import settings
from app.database import init_db
from app.dependencies import get_knowledge_base_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.AUTO_INIT_COLLECTION:
        loaded_chunks = get_knowledge_base_service().sync(force=False)
        app.state.loaded_chunks = loaded_chunks
    yield


app = FastAPI(
    title="Thai Legal RAG API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": settings.LLM_MODEL_NAME}


@app.exception_handler(AppError)
async def handle_app_error(_request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.public_message})


@app.exception_handler(Exception)
async def handle_unexpected_error(_request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled backend exception")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
