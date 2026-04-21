from typing import List, Optional

from pydantic import BaseModel


class LegalQueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None


class LegalQueryResponse(BaseModel):
    answer: str
    sources: List[str]
    analysis: Optional[str] = None
    confidence: Optional[str] = "high"
    thread_id: Optional[str] = None
    needs_clarification: Optional[bool] = False

