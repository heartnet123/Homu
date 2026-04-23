import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.logging import logger
from app.dependencies import (
    get_ask_question_use_case,
    get_stream_answer_use_case,
    get_thread_service,
)
from app.models.schemas import LegalQueryRequest, LegalQueryResponse

router = APIRouter(tags=["chat"])


@router.post("/ask", response_model=LegalQueryResponse)
async def ask_question(
    request: LegalQueryRequest,
    use_case=Depends(get_ask_question_use_case),
):
    return await use_case.execute(request)


@router.post("/ask/stream")
async def ask_question_stream(
    request: LegalQueryRequest,
    use_case=Depends(get_stream_answer_use_case),
):
    thread_id, initial_state = await use_case.start(request)

    async def generate():
        try:
            async for event in use_case.graph.astream_events(initial_state, version="v2"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content}, ensure_ascii=False)}\n\n"
                elif kind == "on_chain_end":
                    output = event["data"].get("output")
                    if isinstance(output, dict) and "messages" in output and "answer" in output:
                        response = use_case.finalize(output, thread_id)
                        metadata = {
                            "type": "metadata",
                            "sources": response.sources,
                            "source_items": [item.model_dump() for item in response.source_items],
                            "needs_clarification": response.needs_clarification,
                            "thread_id": thread_id,
                            "confidence": response.confidence,
                            "expanded_to_all_collections": response.expanded_to_all_collections,
                        }
                        yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"
        except Exception as exc:
            public_message = getattr(exc, "public_message", None)
            error_message = public_message or str(exc) or exc.__class__.__name__
            logger.exception("Unhandled streaming error", extra={"thread_id": thread_id, "error_message": error_message})
            payload = {"type": "error", "content": error_message}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/threads")
async def read_threads(thread_service=Depends(get_thread_service)):
    return [thread.model_dump() for thread in thread_service.list_threads()]


@router.get("/threads/{thread_id}")
async def read_thread_messages(thread_id: str, thread_service=Depends(get_thread_service)):
    return [message.model_dump() for message in thread_service.get_thread_messages(thread_id)]
