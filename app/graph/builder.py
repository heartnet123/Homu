from app.graph.edges import should_clarify
from app.graph.nodes import create_nodes
from app.models.state import LegalRAGState


class _LegacyWorkflowAdapter:
    def __init__(self, embedding_service, llm_service):
        self.embedding_service = embedding_service
        self.llm_service = llm_service

    async def retrieve(self, state):
        docs = self.embedding_service.search(state["query"], n_results=3)
        return {
            "retrieved_docs": docs,
            "source_items": [],
            "sources": docs,
            "retrieval_confidence": 1.0 if docs else 0.0,
            "expanded_to_all_collections": False,
            "iteration": state.get("iteration", 0) + 1,
        }

    async def analyze(self, state):
        context = "\n\n".join(state.get("retrieved_docs", []))
        if hasattr(self.llm_service, "analyze_context"):
            analysis = await self.llm_service.analyze_context(state["query"], context, model_name=state.get("model"))
            sufficient = analysis.sufficient
            raw_analysis = analysis.raw_analysis
        else:
            if hasattr(self.llm_service, "acheck_context_sufficiency"):
                raw_analysis = await self.llm_service.acheck_context_sufficiency(state["query"], context, model_name=state.get("model"))
            else:
                raw_analysis = self.llm_service.check_context_sufficiency(state["query"], context)
            sufficient = not str(raw_analysis).startswith("NEEDS_CLARIFICATION")
            analysis = None
        return {
            "analysis": raw_analysis,
            "clarification_result": analysis,
            "needs_clarification": not sufficient,
        }

    async def generate(self, state):
        context = "\n\n".join(state.get("retrieved_docs", []))
        if hasattr(self.llm_service, "generate_answer"):
            if hasattr(self.llm_service, "agenerate_answer"):
                answer = await self.llm_service.agenerate_answer(state["query"], context, model_name=state.get("model"))
            else:
                answer = self.llm_service.generate_answer(state["query"], context)
        else:
            answer = ""
        from langchain_core.messages import AIMessage

        return {"answer": answer, "messages": [AIMessage(content=answer)]}

    async def clarify(self, state):
        raw_analysis = state.get("analysis") or "NEEDS_CLARIFICATION: กรุณาระบุข้อเท็จจริงเพิ่มเติม"
        detail = str(raw_analysis).replace("NEEDS_CLARIFICATION:", "", 1).strip()
        answer = f"กรุณาให้ข้อมูลเพิ่มเติม: {detail}"
        from langchain_core.messages import AIMessage

        return {"answer": answer, "messages": [AIMessage(content=answer)]}


def build_legal_rag_graph(workflow_service=None, embedding_service=None, llm_service=None):
    from langgraph.graph import END, START, StateGraph

    if workflow_service is None:
        if embedding_service is not None and llm_service is not None:
            workflow_service = _LegacyWorkflowAdapter(embedding_service, llm_service)
        else:
            from app.dependencies import get_workflow_service

            workflow_service = get_workflow_service()

    retrieve_node, analyze_node, generate_node, clarify_node = create_nodes(
        workflow_service=workflow_service,
    )

    workflow = StateGraph(LegalRAGState)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("clarify", clarify_node)

    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "analyze")
    workflow.add_conditional_edges(
        "analyze",
        should_clarify,
        {
            "clarify": "clarify",
            "generate": "generate",
        },
    )
    workflow.add_edge("clarify", END)
    workflow.add_edge("generate", END)

    return workflow.compile()
