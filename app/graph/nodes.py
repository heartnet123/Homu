from app.models.state import LegalRAGState


def create_nodes(workflow_service):
    async def retrieve_node(state: LegalRAGState) -> dict:
        return await workflow_service.retrieve(state)

    async def analyze_node(state: LegalRAGState) -> dict:
        return await workflow_service.analyze(state)

    async def generate_node(state: LegalRAGState) -> dict:
        return await workflow_service.generate(state)

    async def clarify_node(state: LegalRAGState) -> dict:
        return await workflow_service.clarify(state)

    return retrieve_node, analyze_node, generate_node, clarify_node
