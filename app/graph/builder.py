from app.graph.edges import should_clarify
from app.graph.nodes import create_nodes
from app.models.state import LegalRAGState


def build_legal_rag_graph(embedding_service=None, llm_service=None):
    from langgraph.graph import END, START, StateGraph

    if embedding_service is None or llm_service is None:
        from app.dependencies import get_embedding_service, get_llm_service

        embedding_service = embedding_service or get_embedding_service()
        llm_service = llm_service or get_llm_service()

    retrieve_node, analyze_node, generate_node, clarify_node = create_nodes(
        embedding_service=embedding_service,
        llm_service=llm_service,
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

