import asyncio
import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

from fastapi.testclient import TestClient


def install_fake_message_modules() -> None:
    messages_module = ModuleType("langchain_core.messages")

    class BaseMessage:
        def __init__(self, content: str):
            self.content = content

    class HumanMessage(BaseMessage):
        pass

    class AIMessage(BaseMessage):
        pass

    class SystemMessage(BaseMessage):
        pass

    messages_module.BaseMessage = BaseMessage
    messages_module.HumanMessage = HumanMessage
    messages_module.AIMessage = AIMessage
    messages_module.SystemMessage = SystemMessage

    langchain_core_module = ModuleType("langchain_core")
    langchain_core_module.messages = messages_module

    sys.modules["langchain_core"] = langchain_core_module
    sys.modules["langchain_core.messages"] = messages_module


def install_fake_langgraph_modules() -> None:
    message_module = ModuleType("langgraph.graph.message")
    message_module.add_messages = lambda current, new: (current or []) + (new or [])

    graph_module = ModuleType("langgraph.graph")
    graph_module.START = "__start__"
    graph_module.END = "__end__"

    class StateGraph:
        def __init__(self, _state_type):
            self.nodes = {}
            self.edges = {}
            self.conditional_edges = {}

        def add_node(self, name, fn):
            self.nodes[name] = fn

        def add_edge(self, source, target):
            self.edges[source] = target

        def add_conditional_edges(self, source, router, mapping):
            self.conditional_edges[source] = (router, mapping)

        def compile(self):
            parent = self

            class CompiledGraph:
                async def ainvoke(self, initial_state):
                    state = dict(initial_state)
                    current = parent.edges[graph_module.START]

                    while current != graph_module.END:
                        updates = await parent.nodes[current](state)
                        state.update(updates)
                        if current in parent.conditional_edges:
                            router, mapping = parent.conditional_edges[current]
                            current = mapping[router(state)]
                        else:
                            current = parent.edges[current]
                    return state

                def invoke(self, initial_state):
                    return asyncio.run(self.ainvoke(initial_state))

            return CompiledGraph()

    graph_module.StateGraph = StateGraph

    langgraph_module = ModuleType("langgraph")
    langgraph_module.graph = graph_module

    sys.modules["langgraph"] = langgraph_module
    sys.modules["langgraph.graph"] = graph_module
    sys.modules["langgraph.graph.message"] = message_module


class DocumentLoaderTests(unittest.TestCase):
    def test_document_loader_extracts_structured_chunks(self):
        paragraphs = [
            "หมวด 1 บททั่วไป",
            "มาตรา 5 นายจ้างต้องปฏิบัติตามกฎหมาย",
            "ลูกจ้างมีสิทธิได้รับค่าจ้าง",
        ]

        docx_module = ModuleType("docx")
        docx_module.Document = lambda _path: type(
            "Doc",
            (),
            {"paragraphs": [type("Paragraph", (), {"text": text}) for text in paragraphs]},
        )()
        sys.modules["docx"] = docx_module

        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "พรบ.เเรงงาน.docx"
            doc_path.touch()

            module = importlib.import_module("app.infrastructure.document_loader")
            loader = module.DocumentLoader(str(doc_path))
            chunks = loader.load()

        self.assertEqual(chunks[0].text, "[พรบ.เเรงงาน] หมวด 1 บททั่วไป")
        self.assertEqual(chunks[0].collection_id, "default")
        self.assertEqual(chunks[1].article, "มาตรา 5")
        self.assertEqual(
            chunks[2].text,
            "[พรบ.เเรงงาน] [หมวด 1 บททั่วไป] [มาตรา 5] ลูกจ้างมีสิทธิได้รับค่าจ้าง",
        )
        self.assertTrue(chunks[2].metadata["source_path"].endswith(".docx"))


class GraphBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_fake_message_modules()
        install_fake_langgraph_modules()

    def test_graph_generates_answer_when_context_is_sufficient(self):
        builder_module = importlib.import_module("app.graph.builder")
        HumanMessage = importlib.import_module("langchain_core.messages").HumanMessage

        class FakeEmbeddingService:
            def search(self, query: str, n_results: int = 3):
                return ["[พรบ.เเรงงาน] [มาตรา 5] ลูกจ้างมีสิทธิได้รับค่าจ้าง"]

        class FakeLLMService:
            def check_context_sufficiency(self, query: str, context: str) -> str:
                return "SUFFICIENT"

            def generate_answer(self, query: str, context: str) -> str:
                return "อ้างอิงมาตรา 5 ลูกจ้างมีสิทธิได้รับค่าจ้าง"

        graph = builder_module.build_legal_rag_graph(
            embedding_service=FakeEmbeddingService(),
            llm_service=FakeLLMService(),
        )

        result = asyncio.run(
            graph.ainvoke(
                {
                    "messages": [HumanMessage(content="ลูกจ้างมีสิทธิอะไรบ้าง")],
                    "query": "ลูกจ้างมีสิทธิอะไรบ้าง",
                    "thread_id": "thread-1",
                    "retrieved_docs": [],
                    "source_items": [],
                    "sources": [],
                    "analysis": None,
                    "clarification_result": None,
                    "answer": None,
                    "iteration": 0,
                    "needs_clarification": False,
                    "model": None,
                    "collection_id": None,
                    "search_strategy": "hybrid",
                    "confidence_threshold": 0.5,
                    "retrieval_confidence": 0.0,
                    "expanded_to_all_collections": False,
                }
            )
        )

        self.assertEqual(result["analysis"], "SUFFICIENT")
        self.assertFalse(result["needs_clarification"])
        self.assertEqual(result["answer"], "อ้างอิงมาตรา 5 ลูกจ้างมีสิทธิได้รับค่าจ้าง")

    def test_graph_routes_to_clarification_when_analysis_flags_missing_context(self):
        builder_module = importlib.import_module("app.graph.builder")
        HumanMessage = importlib.import_module("langchain_core.messages").HumanMessage

        class FakeEmbeddingService:
            def search(self, query: str, n_results: int = 3):
                return ["[พรบ.เเรงงาน] [มาตรา 119] เลิกจ้างกรณีทุจริต"]

        class FakeLLMService:
            def check_context_sufficiency(self, query: str, context: str) -> str:
                return "NEEDS_CLARIFICATION: ต้องทราบว่าลูกจ้างทำผิดอย่างไร"

        graph = builder_module.build_legal_rag_graph(
            embedding_service=FakeEmbeddingService(),
            llm_service=FakeLLMService(),
        )

        result = asyncio.run(
            graph.ainvoke(
                {
                    "messages": [HumanMessage(content="เลิกจ้างได้ไหม")],
                    "query": "เลิกจ้างได้ไหม",
                    "thread_id": "thread-2",
                    "retrieved_docs": [],
                    "source_items": [],
                    "sources": [],
                    "analysis": None,
                    "clarification_result": None,
                    "answer": None,
                    "iteration": 0,
                    "needs_clarification": False,
                    "model": None,
                    "collection_id": None,
                    "search_strategy": "hybrid",
                    "confidence_threshold": 0.5,
                    "retrieval_confidence": 0.0,
                    "expanded_to_all_collections": False,
                }
            )
        )

        self.assertTrue(result["needs_clarification"])
        self.assertIn("กรุณาให้ข้อมูลเพิ่มเติม", result["answer"])


class ThreadRepositoryTests(unittest.TestCase):
    def test_repository_stores_timezone_aware_messages_and_sources(self):
        from app.domain.models import SourceItem
        from app.infrastructure.repositories.thread_repository import SQLiteThreadRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "threads.db"
            repo = SQLiteThreadRepository(db_path)
            repo.init_db()

            thread_id = repo.create_thread("ทดสอบ")
            repo.add_message(
                thread_id,
                "ai",
                "คำตอบ",
                sources=["legacy-source"],
                source_items=[
                    SourceItem(
                        chunk_id="chunk-1",
                        text="ข้อความอ้างอิง",
                        document="doc",
                        collection_id="labor",
                    )
                ],
            )

            messages = repo.get_thread_messages(thread_id)

        self.assertEqual(messages[0].sources, ["legacy-source"])
        self.assertEqual(messages[0].source_items[0].chunk_id, "chunk-1")
        self.assertIn("+00:00", messages[0].created_at)


class HybridRetrieverTests(unittest.TestCase):
    def test_hybrid_rrf_prefers_shared_hits(self):
        from app.domain.models import SourceItem
        from app.rag.retrieval.hybrid import HybridRetriever

        class FakeVectorStore:
            def search(self, query, *, collection_id=None, n_results=3):
                return [
                    SourceItem(chunk_id="a", text="A", document="doc", collection_id="default", score=0.9),
                    SourceItem(chunk_id="b", text="B", document="doc", collection_id="default", score=0.7),
                ]

        class FakeBM25Store:
            def search(self, query, *, collection_id=None, n_results=3):
                return [
                    SourceItem(chunk_id="b", text="B", document="doc", collection_id="default", score=12.0),
                    SourceItem(chunk_id="c", text="C", document="doc", collection_id="default", score=9.0),
                ]

        retriever = HybridRetriever(FakeVectorStore(), FakeBM25Store())
        result = asyncio.run(
            retriever.search(
                "query",
                collection_id=None,
                strategy="hybrid",
                n_results=3,
                confidence_threshold=0.5,
            )
        )

        self.assertEqual(result.sources[0].chunk_id, "b")
        self.assertEqual(result.sources[0].retrieval_method, "hybrid")

    def test_low_confidence_collection_search_expands_scope(self):
        from app.domain.models import SourceItem
        from app.rag.retrieval.hybrid import HybridRetriever

        class FakeVectorStore:
            def search(self, query, *, collection_id=None, n_results=3):
                if collection_id == "labor":
                    return [SourceItem(chunk_id="l1", text="labor", document="doc", collection_id="labor", score=0.1)]
                return [SourceItem(chunk_id="g1", text="global", document="doc", collection_id="tax", score=0.9)]

        class FakeBM25Store:
            def search(self, query, *, collection_id=None, n_results=3):
                return []

        retriever = HybridRetriever(FakeVectorStore(), FakeBM25Store())
        result = asyncio.run(
            retriever.search(
                "query",
                collection_id="labor",
                strategy="vector",
                n_results=3,
                confidence_threshold=0.5,
            )
        )

        self.assertTrue(result.expanded_to_all_collections)
        self.assertEqual(result.sources[0].collection_id, "tax")


class FastAPITests(unittest.TestCase):
    def setUp(self):
        os.environ["AUTO_INIT_COLLECTION"] = "false"
        for module_name in list(sys.modules):
            if module_name.startswith("app."):
                sys.modules.pop(module_name)

    def test_ask_and_thread_endpoints_remain_compatible(self):
        main_module = importlib.import_module("app.main")
        dependencies_module = importlib.import_module("app.dependencies")
        client = TestClient(main_module.app)

        class FakeAskUseCase:
            async def execute(self, request):
                from app.models.schemas import LegalQueryResponse
                from app.domain.models import SourceItem

                return LegalQueryResponse(
                    answer="คำตอบทดสอบ",
                    sources=["[Doc: test] ข้อความอ้างอิง"],
                    source_items=[
                        SourceItem(
                            chunk_id="chunk-1",
                            text="ข้อความอ้างอิง",
                            document="test",
                            collection_id="default",
                        )
                    ],
                    analysis="SUFFICIENT",
                    confidence=0.91,
                    thread_id="thread-123",
                )

        class FakeThreadRepository:
            def get_threads(self):
                from app.domain.models import ThreadSummary

                return [ThreadSummary(id="thread-123", title="หัวข้อ", created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")]

            def get_thread_messages(self, thread_id):
                from app.domain.models import ThreadMessage

                return [ThreadMessage(role="ai", content="คำตอบทดสอบ", created_at="2024-01-01T00:00:00+00:00")]

        class FakeThreadService:
            def list_threads(self):
                return FakeThreadRepository().get_threads()

            def get_thread_messages(self, thread_id):
                return FakeThreadRepository().get_thread_messages(thread_id)

        class FakeStreamUseCase:
            def __init__(self):
                self.thread_repository = FakeThreadRepository()
                self.graph = self

            async def start(self, request):
                return "thread-123", {"query": request.query}

            async def astream_events(self, initial_state, version="v2"):
                yield {"event": "on_chat_model_stream", "data": {"chunk": type("Chunk", (), {"content": "คำ"})()}}
                yield {"event": "on_chain_end", "data": {"output": {"messages": ["done"], "answer": "คำตอบสตรีม", "sources": ["legacy"], "source_items": [], "needs_clarification": False, "retrieval_confidence": 0.8}}}

            def finalize(self, output, thread_id):
                from app.models.schemas import LegalQueryResponse

                return LegalQueryResponse(
                    answer=output["answer"],
                    sources=["legacy"],
                    source_items=[],
                    confidence=0.8,
                    thread_id=thread_id,
                    needs_clarification=False,
                )

        main_module.app.dependency_overrides[dependencies_module.get_ask_question_use_case] = lambda: FakeAskUseCase()
        main_module.app.dependency_overrides[dependencies_module.get_stream_answer_use_case] = lambda: FakeStreamUseCase()
        main_module.app.dependency_overrides[dependencies_module.get_thread_service] = lambda: FakeThreadService()

        ask_response = client.post("/api/v1/ask", json={"query": "ลาป่วยได้กี่วัน"})
        threads_response = client.get("/api/v1/threads")
        messages_response = client.get("/api/v1/threads/thread-123")

        main_module.app.dependency_overrides.clear()

        self.assertEqual(ask_response.status_code, 200)
        self.assertEqual(ask_response.json()["answer"], "คำตอบทดสอบ")
        self.assertEqual(threads_response.status_code, 200)
        self.assertEqual(threads_response.json()[0]["id"], "thread-123")
        self.assertEqual(messages_response.status_code, 200)
        self.assertEqual(messages_response.json()[0]["content"], "คำตอบทดสอบ")

    def test_streaming_documents_ingest_and_capabilities_endpoints(self):
        main_module = importlib.import_module("app.main")
        dependencies_module = importlib.import_module("app.dependencies")
        client = TestClient(main_module.app)

        class FakeThreadService:
            def list_threads(self):
                return []

            def get_thread_messages(self, thread_id):
                return []

        class FakeThreadRepository:
            def get_threads(self):
                return []

            def get_thread_messages(self, thread_id):
                return []

        class FakeStreamUseCase:
            def __init__(self):
                self.thread_repository = FakeThreadRepository()
                self.graph = self

            async def start(self, request):
                return "thread-stream", {"query": request.query}

            async def astream_events(self, initial_state, version="v2"):
                yield {"event": "on_chat_model_stream", "data": {"chunk": type("Chunk", (), {"content": "สวัสดี"})()}}
                yield {"event": "on_chain_end", "data": {"output": {"messages": ["done"], "answer": "สวัสดี", "sources": ["legacy-source"], "source_items": [], "needs_clarification": False, "retrieval_confidence": 0.7, "expanded_to_all_collections": False}}}

            def finalize(self, output, thread_id):
                from app.models.schemas import LegalQueryResponse

                return LegalQueryResponse(
                    answer="สวัสดี",
                    sources=["legacy-source"],
                    source_items=[],
                    confidence=0.7,
                    thread_id=thread_id,
                )

        class FakeDocumentService:
            def list_documents(self):
                return [{"name": "law.docx", "size": 10, "modified": 1.0, "collection_id": "default", "relative_path": "law.docx"}]

            async def upload_documents(self, files, *, collection_id=None):
                return [upload.filename for upload in files]

            def delete_document(self, filename):
                return filename

        class FakeKnowledgeBaseService:
            def sync(self, *, force=True):
                return 7

            def get_collections(self):
                from app.domain.models import CollectionInfo

                return [CollectionInfo(id="default", name="default", document_count=1)]

        main_module.app.dependency_overrides[dependencies_module.get_stream_answer_use_case] = lambda: FakeStreamUseCase()
        main_module.app.dependency_overrides[dependencies_module.get_document_service] = lambda: FakeDocumentService()
        main_module.app.dependency_overrides[dependencies_module.get_knowledge_base_service] = lambda: FakeKnowledgeBaseService()
        main_module.app.dependency_overrides[dependencies_module.get_thread_service] = lambda: FakeThreadService()
        main_module.app.dependency_overrides[dependencies_module.get_capabilities_payload] = lambda: {
            "models": ["gpt-5.4-mini"],
            "search_strategies": ["vector", "bm25", "hybrid"],
            "default_model": "gpt-5.4-mini",
            "default_search_strategy": "hybrid",
            "default_confidence_threshold": 0.5,
            "collections": [{"id": "default", "name": "default", "document_count": 1}],
        }

        with client.stream("POST", "/api/v1/ask/stream", json={"query": "hello"}) as response:
            chunks = list(response.iter_text())

        docs_response = client.get("/api/v1/documents")
        upload_response = client.post(
            "/api/v1/upload",
            files=[("files", ("law.docx", b"binary", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        )
        ingest_response = client.post("/api/v1/ingest")
        delete_response = client.delete("/api/v1/documents/law.docx")
        capabilities_response = client.get("/api/v1/capabilities")

        main_module.app.dependency_overrides.clear()

        stream_text = "".join(chunks)
        self.assertIn('"type": "token"', stream_text)
        self.assertIn('"type": "metadata"', stream_text)
        self.assertEqual(docs_response.status_code, 200)
        self.assertEqual(upload_response.status_code, 200)
        self.assertEqual(upload_response.json()["files"], ["law.docx"])
        self.assertEqual(ingest_response.json()["chunks"], 7)
        self.assertEqual(delete_response.json()["message"], "Deleted law.docx")
        self.assertEqual(capabilities_response.json()["search_strategies"], ["vector", "bm25", "hybrid"])


if __name__ == "__main__":
    unittest.main()
