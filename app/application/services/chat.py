from typing import Any

from app.core.settings import settings
from app.domain.models import ClarificationResult, SourceItem
from app.models.schemas import LegalQueryRequest, LegalQueryResponse


def _create_human_message(content: str):
    from langchain_core.messages import HumanMessage

    return HumanMessage(content=content)


def _create_ai_message(content: str):
    from langchain_core.messages import AIMessage

    return AIMessage(content=content)


class LegalAssistantWorkflowService:
    def __init__(self, knowledge_base_service, retriever, llm_service):
        self.knowledge_base_service = knowledge_base_service
        self.retriever = retriever
        self.llm_service = llm_service

    @staticmethod
    def to_legacy_sources(source_items: list[SourceItem]) -> list[str]:
        return [item.as_legacy_text() for item in source_items]

    async def retrieve(self, state: dict[str, Any]) -> dict[str, Any]:
        self.knowledge_base_service.ensure_ready()
        search_result = await self.retriever.search(
            state["query"],
            collection_id=state.get("collection_id"),
            strategy=state.get("search_strategy"),
            n_results=settings.TOP_K_RESULTS,
            confidence_threshold=state.get("confidence_threshold") or settings.DEFAULT_CONFIDENCE_THRESHOLD,
        )
        return {
            "retrieved_docs": [source.text for source in search_result.sources],
            "source_items": search_result.sources,
            "sources": self.to_legacy_sources(search_result.sources),
            "retrieval_confidence": search_result.confidence,
            "expanded_to_all_collections": search_result.expanded_to_all_collections,
            "iteration": state.get("iteration", 0) + 1,
        }

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        context = "\n\n".join(state.get("retrieved_docs", []))
        analysis = await self.llm_service.analyze_context(
            state["query"],
            context,
            model_name=state.get("model"),
        )
        return {
            "analysis": analysis.raw_analysis,
            "clarification_result": analysis,
            "needs_clarification": not analysis.sufficient,
        }

    async def generate(self, state: dict[str, Any]) -> dict[str, Any]:
        context = "\n\n".join(state.get("retrieved_docs", []))
        answer = await self.llm_service.generate_answer(
            state["query"],
            context,
            model_name=state.get("model"),
        )
        return {
            "answer": answer,
            "messages": [_create_ai_message(answer)],
        }

    async def clarify(self, state: dict[str, Any]) -> dict[str, Any]:
        clarification: ClarificationResult | None = state.get("clarification_result")
        question = None
        if clarification is not None:
            question = clarification.clarification_question
        if not question:
            question = "กรุณาระบุข้อเท็จจริงเพิ่มเติมเพื่อให้ตอบได้อย่างถูกต้อง"
        answer = f"กรุณาให้ข้อมูลเพิ่มเติม: {question}"
        return {
            "answer": answer,
            "messages": [_create_ai_message(answer)],
        }


def build_initial_state(request: LegalQueryRequest, thread_id: str) -> dict[str, Any]:
    return {
        "messages": [_create_human_message(request.query)],
        "query": request.query,
        "thread_id": thread_id,
        "retrieved_docs": [],
        "source_items": [],
        "sources": [],
        "analysis": None,
        "clarification_result": None,
        "answer": None,
        "iteration": 0,
        "needs_clarification": False,
        "model": request.model,
        "collection_id": request.collection_id,
        "search_strategy": request.search_strategy or settings.DEFAULT_SEARCH_STRATEGY,
        "confidence_threshold": request.confidence_threshold or settings.DEFAULT_CONFIDENCE_THRESHOLD,
        "retrieval_confidence": 0.0,
        "expanded_to_all_collections": False,
    }


def build_response_from_result(result: dict[str, Any], thread_id: str) -> LegalQueryResponse:
    source_items = result.get("source_items", [])
    return LegalQueryResponse(
        answer=result.get("answer") or "",
        sources=result.get("sources", []),
        source_items=source_items,
        analysis=result.get("analysis"),
        confidence=result.get("retrieval_confidence"),
        thread_id=thread_id,
        needs_clarification=result.get("needs_clarification", False),
        collection_id=result.get("collection_id"),
        expanded_to_all_collections=result.get("expanded_to_all_collections", False),
    )


class AskQuestionUseCase:
    def __init__(self, graph, thread_repository):
        self.graph = graph
        self.thread_repository = thread_repository

    async def execute(self, request: LegalQueryRequest) -> LegalQueryResponse:
        thread_id = request.thread_id
        if not thread_id:
            thread_id = self.thread_repository.create_thread(
                title=request.query[:50] + ("..." if len(request.query) > 50 else "")
            )

        self.thread_repository.add_message(thread_id, "user", request.query)
        result = await self.graph.ainvoke(build_initial_state(request, thread_id))
        response = build_response_from_result(result, thread_id)
        self.thread_repository.add_message(
            thread_id,
            "ai",
            response.answer,
            sources=response.sources,
            source_items=response.source_items,
            needs_clarification=response.needs_clarification,
        )
        return response


class StreamAnswerUseCase:
    def __init__(self, graph, thread_repository):
        self.graph = graph
        self.thread_repository = thread_repository

    async def start(self, request: LegalQueryRequest) -> tuple[str, dict[str, Any]]:
        thread_id = request.thread_id
        if not thread_id:
            thread_id = self.thread_repository.create_thread(
                title=request.query[:50] + ("..." if len(request.query) > 50 else "")
            )

        self.thread_repository.add_message(thread_id, "user", request.query)
        return thread_id, build_initial_state(request, thread_id)

    def finalize(self, output: dict[str, Any], thread_id: str) -> LegalQueryResponse:
        response = build_response_from_result(output, thread_id)
        self.thread_repository.add_message(
            thread_id,
            "ai",
            response.answer,
            sources=response.sources,
            source_items=response.source_items,
            needs_clarification=response.needs_clarification,
        )
        return response
