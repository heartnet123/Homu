from app.config import settings
from app.dependencies import get_document_loader, get_embedding_service, get_legal_rag_graph


def _create_human_message(content: str):
    from langchain_core.messages import HumanMessage

    return HumanMessage(content=content)


def bootstrap() -> None:
    loader = get_document_loader()
    embed_service = get_embedding_service()
    documents = loader.load()
    embed_service.initialize_collection(documents)


def ask_legal_question(query: str) -> tuple[str, list[str]]:
    graph = get_legal_rag_graph()
    result = graph.invoke(
        {
            "messages": [_create_human_message(query)],
            "query": query,
            "retrieved_docs": [],
            "analysis": None,
            "answer": None,
            "sources": [],
            "iteration": 0,
            "needs_clarification": False,
        }
    )
    return result["answer"], result.get("sources", [])


def main() -> None:
    bootstrap()

    print("\n==================================================")
    print("🧑‍⚖️ ระบบที่ปรึกษากฎหมายแรงงาน AI (LangGraph + FastAPI backend)")
    print(f"ใช้โมเดลตอบคำถาม: {settings.LLM_MODEL_NAME}")
    print("พิมพ์ 'exit' เพื่อออก")
    print("==================================================")

    while True:
        user_query = input("\n[You] ถามคำถาม: ")

        if user_query.lower() in {"exit", "quit", "q"}:
            print("ลาก่อนครับ!")
            break

        if not user_query.strip():
            continue

        print("[AI] กำลังค้นหาข้อมูลและประมวลผลคำตอบ...", flush=True)

        try:
            answer, sources = ask_legal_question(user_query)
            print("\n--------------------------------------------------")
            print(f"✅ คำตอบ:\n{answer}")
            print("--------------------------------------------------")
            print("📚 อ้างอิงจากข้อความ (โชว์ 100 ตัวอักษรแรก):")
            for idx, source in enumerate(sources, start=1):
                print(f"  {idx}. {source[:100]}...")
        except Exception as exc:
            print(f"\n❌ เกิดข้อผิดพลาด: {exc}")


if __name__ == "__main__":
    main()
