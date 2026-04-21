from app.models.state import LegalRAGState


def should_clarify(state: LegalRAGState) -> str:
    if state.get("needs_clarification", False):
        return "clarify"
    return "generate"


def should_continue(state: LegalRAGState) -> str:
    if state.get("iteration", 0) >= 3:
        return "end"
    return "continue"

