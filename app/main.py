import os
import shutil
from typing import List
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File

from app.config import settings
from app.dependencies import (
    get_document_loader,
    get_embedding_service,
    get_legal_rag_graph,
)
from app.models.schemas import LegalQueryRequest, LegalQueryResponse
from app.database import init_db, create_thread, add_message, get_threads, get_thread_messages


def _create_human_message(content: str):
    from langchain_core.messages import HumanMessage

    return HumanMessage(content=content)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post(f"{settings.API_V1_PREFIX}/ask", response_model=LegalQueryResponse)
async def ask_question(
    request: LegalQueryRequest,
    legal_rag_graph=Depends(get_legal_rag_graph),
):
    try:
        thread_id = request.thread_id
        if not thread_id:
            thread_id = create_thread(title=request.query[:50] + ("..." if len(request.query) > 50 else ""))
            
        add_message(thread_id, "user", request.query)

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

        answer = result.get("answer")
        sources = result.get("sources", [])[: settings.TOP_K_RESULTS]
        needs_clarification = result.get("needs_clarification", False)

        add_message(thread_id, "ai", answer, sources, needs_clarification)

        return LegalQueryResponse(
            answer=answer,
            sources=sources,
            analysis=result.get("analysis"),
            thread_id=thread_id,
            needs_clarification=needs_clarification
        )
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=500, detail=str(exc)) from exc


import json
from fastapi.responses import StreamingResponse

@app.post(f"{settings.API_V1_PREFIX}/ask/stream")
async def ask_question_stream(
    request: LegalQueryRequest,
    legal_rag_graph=Depends(get_legal_rag_graph),
):
    try:
        thread_id = request.thread_id
        if not thread_id:
            thread_id = create_thread(title=request.query[:50] + ("..." if len(request.query) > 50 else ""))
            
        add_message(thread_id, "user", request.query)

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

        async def generate():
            try:
                # Capture stream events from LangGraph
                async for event in legal_rag_graph.astream_events(initial_state, version="v2"):
                    kind = event["event"]
                    if kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        if chunk.content:
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk.content}, ensure_ascii=False)}\n\n"
                    elif kind == "on_chain_end":
                        output = event["data"].get("output")
                        # State dictionary at the very end of the graph execution
                        if isinstance(output, dict) and "messages" in output and "answer" in output:
                            final_answer = output.get("answer")
                            final_sources = output.get("sources", [])[: settings.TOP_K_RESULTS]
                            needs_clar = output.get("needs_clarification", False)

                            yield f"data: {json.dumps({'type': 'metadata', 'sources': final_sources, 'needs_clarification': needs_clar, 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

                            add_message(thread_id, "ai", final_answer, final_sources, needs_clar)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.get(f"{settings.API_V1_PREFIX}/threads")
async def read_threads():
    try:
        return get_threads()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.get(f"{settings.API_V1_PREFIX}/threads/{{thread_id}}")
async def read_thread_messages(thread_id: str):
    try:
        return get_thread_messages(thread_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(f"{settings.API_V1_PREFIX}/documents")
async def list_documents():
    doc_path = Path(settings.DOC_PATH)
    if not doc_path.exists():
        return []
    
    files = []
    for f in doc_path.glob("*.docx"):
        stats = f.stat()
        files.append({
            "name": f.name,
            "size": stats.st_size,
            "modified": stats.st_mtime
        })
    return sorted(files, key=lambda x: x["name"])


@app.post(f"{settings.API_V1_PREFIX}/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    doc_dir = Path(settings.DOC_PATH)
    doc_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    for file in files:
        if not file.filename.endswith(".docx"):
            continue
            
        file_path = doc_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        uploaded_files.append(file.filename)
        
    return {"message": f"Successfully uploaded {len(uploaded_files)} files", "files": uploaded_files}


@app.delete(f"{settings.API_V1_PREFIX}/documents/{{filename}}")
async def delete_document(filename: str):
    file_path = Path(settings.DOC_PATH) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    os.remove(file_path)
    return {"message": f"Deleted {filename}"}


@app.post(f"{settings.API_V1_PREFIX}/ingest")
async def ingest_documents(
    loader=Depends(get_document_loader),
    embed_service=Depends(get_embedding_service)
):
    try:
        documents = loader.load()
        embed_service.initialize_collection(documents, force=True)
        return {"message": "Knowledge base synchronized successfully", "chunks": len(documents)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": settings.LLM_MODEL_NAME}

