from app.config import settings


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
        from langchain_openai import ChatOpenAI

        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.0,
        )

    def get_system_prompt(self) -> str:
        return STRICT_LEGAL_SYSTEM_PROMPT

    def check_context_sufficiency(self, query: str, context: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(
                content=(
                    "คุณเป็นผู้ช่วยวิเคราะห์กฎหมาย ให้ตอบคำเดียวว่า SUFFICIENT "
                    "หรือขึ้นต้นด้วย NEEDS_CLARIFICATION: ตามด้วยสิ่งที่ต้องถามเพิ่ม"
                )
            ),
            HumanMessage(
                content=(
                    f"[ข้อมูลอ้างอิง]\n{context}\n\n"
                    f"คำถาม: {query}\n"
                    "วิเคราะห์ว่าข้อมูลพอหรือยัง"
                )
            ),
        ]
        response = self.llm.invoke(messages)
        return response.content

    def generate_answer(self, query: str, context: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=f"[ข้อมูลอ้างอิง]\n{context}\n\nคำถาม: {query}"),
        ]
        response = self.llm.invoke(messages)
        return response.content

