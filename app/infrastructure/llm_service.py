import json
import re

from app.core.errors import BadRequestError, ConfigurationError, ExternalServiceError
from app.core.settings import settings
from app.domain.models import ClarificationResult


STRICT_LEGAL_SYSTEM_PROMPT = """คุณคือ "ที่ปรึกษากฎหมายแรงงานไทยระดับโลก"
หน้าที่ของคุณคือตอบคำถามโดยอ้างอิงจากข้อมูลอ้างอิงที่ได้รับมาเท่านั้น
ห้ามใช้ความรู้ภายนอกหรือคาดเดาเด็ดขาด

กฎเหล็ก:
1. ระบุเลขมาตราหรือข้อที่เกี่ยวข้องเสมอ
2. ตรวจสอบเงื่อนไขบังคับใช้อย่างเคร่งครัดก่อนสรุป
3. ถ้าข้อเท็จจริงไม่พอ ให้ระบุสิ่งที่ต้องถามเพิ่มอย่างชัดเจน
4. ถ้าฐานข้อมูลไม่ครอบคลุม ให้ตอบว่าฐานข้อมูลปัจจุบันไม่ครอบคลุมประเด็นนี้
5. ห้ามแต่งข้อมูลหรืออ้างกฎหมายที่ไม่ได้อยู่ในบริบท
"""


class LLMService:
    def __init__(self):
        self.default_model = settings.LLM_MODEL_NAME
        self.api_key = settings.OPENAI_API_KEY
        self._llm_cache: dict[str, object] = {}

    def _get_llm(self, model_name: str | None = None):
        from langchain_openai import ChatOpenAI

        if not self.api_key:
            raise ConfigurationError("OPENAI_API_KEY is not configured.")

        target_model = model_name or self.default_model
        if target_model not in settings.SUPPORTED_LLM_MODELS:
            raise BadRequestError(f"Model '{target_model}' is not supported by this backend.")

        if target_model not in self._llm_cache:
            self._llm_cache[target_model] = ChatOpenAI(
                model=target_model,
                api_key=self.api_key,
                temperature=0.0,
            )
        return self._llm_cache[target_model]

    def get_system_prompt(self) -> str:
        return STRICT_LEGAL_SYSTEM_PROMPT

    @staticmethod
    def _extract_json_payload(raw_text: str) -> dict:
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned, flags=re.MULTILINE)
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError("No JSON payload found in model response.")
        return json.loads(match.group(0))

    def _parse_analysis_response(self, raw_text: str) -> ClarificationResult:
        try:
            payload = self._extract_json_payload(raw_text)
            return ClarificationResult(
                sufficient=bool(payload.get("sufficient")),
                clarification_question=payload.get("clarification_question"),
                confidence=float(payload.get("confidence", 0.0)),
                raw_analysis=raw_text,
            )
        except Exception:
            if raw_text.startswith("NEEDS_CLARIFICATION"):
                detail = raw_text.replace("NEEDS_CLARIFICATION:", "", 1).strip() or None
                return ClarificationResult(
                    sufficient=False,
                    clarification_question=detail,
                    confidence=0.0,
                    raw_analysis=raw_text,
                )
            return ClarificationResult(
                sufficient=raw_text.strip().upper() == "SUFFICIENT",
                clarification_question=None,
                confidence=1.0 if raw_text.strip().upper() == "SUFFICIENT" else 0.0,
                raw_analysis=raw_text,
            )

    async def analyze_context(
        self,
        query: str,
        context: str,
        model_name: str | None = None,
    ) -> ClarificationResult:
        from langchain_core.messages import HumanMessage, SystemMessage

        if not context.strip():
            return ClarificationResult(
                sufficient=False,
                clarification_question="ฐานข้อมูลปัจจุบันไม่ครอบคลุมประเด็นนี้ หรือกรุณาระบุข้อเท็จจริงเพิ่มเติม",
                confidence=0.0,
                raw_analysis="NO_CONTEXT",
            )

        llm = self._get_llm(model_name)
        messages = [
            SystemMessage(
                content=(
                    "คุณเป็นผู้ช่วยวิเคราะห์กฎหมาย ให้ตอบ JSON เท่านั้นในรูปแบบ "
                    '{"sufficient": true|false, "clarification_question": string|null, '
                    '"confidence": 0.0}'
                )
            ),
            HumanMessage(
                content=(
                    f"[ข้อมูลอ้างอิง]\n{context}\n\n"
                    f"คำถาม: {query}\n"
                    "วิเคราะห์ว่าข้อมูลพอหรือยัง ถ้าไม่พอให้ระบุคำถามที่ควรถามเพิ่ม 1 ข้อ"
                )
            ),
        ]

        try:
            response = await llm.ainvoke(messages)
        except Exception as exc:
            raise ExternalServiceError("Failed to analyze legal context.") from exc

        return self._parse_analysis_response(response.content)

    async def generate_answer(
        self,
        query: str,
        context: str,
        model_name: str | None = None,
    ) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = self._get_llm(model_name)
        messages = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=f"[ข้อมูลอ้างอิง]\n{context}\n\nคำถาม: {query}"),
        ]

        try:
            response = await llm.ainvoke(messages)
        except Exception as exc:
            raise ExternalServiceError("Failed to generate a legal answer.") from exc

        return response.content

    def get_supported_models(self) -> list[str]:
        return list(settings.SUPPORTED_LLM_MODELS)
