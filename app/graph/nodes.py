from app.config import settings
from app.models.state import LegalRAGState


def _create_ai_message(content: str):
    from langchain_core.messages import AIMessage

    return AIMessage(content=content)


def create_nodes(embedding_service, llm_service):
    def retrieve_node(state: LegalRAGState) -> dict:
        docs = embedding_service.search(
            state["query"],
            n_results=settings.TOP_K_RESULTS,
        )
        return {
            "retrieved_docs": docs,
            "iteration": state.get("iteration", 0) + 1,
        }

    def analyze_node(state: LegalRAGState) -> dict:
        context = "\n\n".join(state["retrieved_docs"])
        analysis = llm_service.check_context_sufficiency(state["query"], context)
        return {
            "analysis": analysis,
            "needs_clarification": analysis.startswith("NEEDS_CLARIFICATION"),
        }

    def generate_node(state: LegalRAGState) -> dict:
        context = "\n\n".join(state["retrieved_docs"])
        answer = llm_service.generate_answer(state["query"], context)
        return {
            "answer": answer,
            "sources": state["retrieved_docs"],
            "messages": [_create_ai_message(answer)],
        }

    def clarify_node(state: LegalRAGState) -> dict:
        analysis = state["analysis"] or "NEEDS_CLARIFICATION: กรุณาระบุข้อเท็จจริงเพิ่มเติม"
        clarification = analysis.replace("NEEDS_CLARIFICATION: ", "", 1)
        answer = f"กรุณาให้ข้อมูลเพิ่มเติม: {clarification}"
        return {
            "answer": answer,
            "messages": [_create_ai_message(answer)],
        }

    return retrieve_node, analyze_node, generate_node, clarify_node

