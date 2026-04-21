import importlib
import os
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


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
                def invoke(self, initial_state):
                    state = dict(initial_state)
                    current = parent.edges[graph_module.START]

                    while current != graph_module.END:
                        updates = parent.nodes[current](state)
                        state.update(updates)
                        if current in parent.conditional_edges:
                            router, mapping = parent.conditional_edges[current]
                            current = mapping[router(state)]
                        else:
                            current = parent.edges[current]

                    return state

            return CompiledGraph()

    graph_module.StateGraph = StateGraph

    langgraph_module = ModuleType("langgraph")
    langgraph_module.graph = graph_module

    sys.modules["langgraph"] = langgraph_module
    sys.modules["langgraph.graph"] = graph_module
    sys.modules["langgraph.graph.message"] = message_module


def install_fake_docx_module(paragraphs: list[str]) -> None:
    docx_module = ModuleType("docx")
    docx_module.Document = lambda _path: SimpleNamespace(
        paragraphs=[SimpleNamespace(text=text) for text in paragraphs]
    )
    sys.modules["docx"] = docx_module


class DocumentLoaderTests(unittest.TestCase):
    def test_document_loader_tags_chapters_articles_and_subparagraphs(self):
        install_fake_docx_module(
            [
                "หมวด 1 บททั่วไป",
                "มาตรา 5 นายจ้างต้องปฏิบัติตามกฎหมาย",
                "ลูกจ้างมีสิทธิได้รับค่าจ้าง",
            ]
        )

        module = importlib.import_module("app.services.document_loader")
        loader = module.DocumentLoader("data/พรบ.เเรงงาน.docx")

        chunks = loader.load()

        self.assertEqual(chunks[0], "[พรบ.เเรงงาน] หมวด 1 บททั่วไป")
        self.assertEqual(
            chunks[1],
            "[พรบ.เเรงงาน] [หมวด 1 บททั่วไป] มาตรา 5 นายจ้างต้องปฏิบัติตามกฎหมาย",
        )
        self.assertEqual(
            chunks[2],
            "[พรบ.เเรงงาน] [หมวด 1 บททั่วไป] [มาตรา 5] ลูกจ้างมีสิทธิได้รับค่าจ้าง",
        )


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
                self.last_query = query
                self.last_n_results = n_results
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

        result = graph.invoke(
            {
                "messages": [HumanMessage(content="ลูกจ้างมีสิทธิอะไรบ้าง")],
                "query": "ลูกจ้างมีสิทธิอะไรบ้าง",
                "retrieved_docs": [],
                "analysis": None,
                "answer": None,
                "sources": [],
                "iteration": 0,
                "needs_clarification": False,
            }
        )

        self.assertEqual(result["analysis"], "SUFFICIENT")
        self.assertFalse(result["needs_clarification"])
        self.assertEqual(result["answer"], "อ้างอิงมาตรา 5 ลูกจ้างมีสิทธิได้รับค่าจ้าง")
        self.assertEqual(len(result["sources"]), 1)

    def test_graph_routes_to_clarification_when_analysis_flags_missing_context(self):
        builder_module = importlib.import_module("app.graph.builder")
        HumanMessage = importlib.import_module("langchain_core.messages").HumanMessage

        class FakeEmbeddingService:
            def search(self, query: str, n_results: int = 3):
                return ["[พรบ.เเรงงาน] [มาตรา 119] เลิกจ้างกรณีทุจริต"]

        class FakeLLMService:
            def check_context_sufficiency(self, query: str, context: str) -> str:
                return "NEEDS_CLARIFICATION: ต้องทราบว่าลูกจ้างทำผิดอย่างไร"

            def generate_answer(self, query: str, context: str) -> str:
                raise AssertionError("generate_answer should not be called")

        graph = builder_module.build_legal_rag_graph(
            embedding_service=FakeEmbeddingService(),
            llm_service=FakeLLMService(),
        )

        result = graph.invoke(
            {
                "messages": [HumanMessage(content="เลิกจ้างได้ไหม")],
                "query": "เลิกจ้างได้ไหม",
                "retrieved_docs": [],
                "analysis": None,
                "answer": None,
                "sources": [],
                "iteration": 0,
                "needs_clarification": False,
            }
        )

        self.assertTrue(result["needs_clarification"])
        self.assertIn("กรุณาให้ข้อมูลเพิ่มเติม", result["answer"])
        self.assertIn("ต้องทราบว่าลูกจ้างทำผิดอย่างไร", result["answer"])


class EmbeddingServiceTests(unittest.TestCase):
    def test_embedding_service_uses_chromadb_compatible_embedding_function(self):
        import chromadb

        module = importlib.import_module("app.services.embedding_service")
        captured: dict[str, object] = {}

        class FakeSentenceTransformer:
            def __init__(self, *args, **kwargs):
                pass

            def encode(self, input, **kwargs):
                return [[0.1, 0.2] for _ in input]

        class FakeClient:
            def get_or_create_collection(self, *, name, embedding_function):
                captured["collection_name"] = name
                captured["embedding_function"] = embedding_function
                return SimpleNamespace()

        fake_sentence_transformers = ModuleType("sentence_transformers")
        fake_sentence_transformers.SentenceTransformer = FakeSentenceTransformer

        with (
            patch.object(chromadb, "PersistentClient", return_value=FakeClient()),
            patch.dict(sys.modules, {"sentence_transformers": fake_sentence_transformers}),
        ):
            module.EmbeddingService()

        self.assertTrue(
            callable(getattr(captured["embedding_function"], "name", None)),
            "Embedding function passed to ChromaDB must implement name()",
        )


class FastAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_fake_message_modules()
        install_fake_langgraph_modules()

    def test_ask_endpoint_returns_graph_response(self):
        os.environ["AUTO_INIT_COLLECTION"] = "false"
        main_module = importlib.import_module("app.main")
        client = importlib.import_module("fastapi.testclient").TestClient(main_module.app)

        class FakeGraph:
            def invoke(self, initial_state):
                return {
                    **initial_state,
                    "answer": "คำตอบทดสอบ",
                    "sources": ["มาตรา 5"],
                    "analysis": "SUFFICIENT",
                }

        main_module.app.dependency_overrides[main_module.get_legal_rag_graph] = lambda: FakeGraph()
        response = client.post("/api/v1/ask", json={"query": "ลาป่วยได้กี่วัน"})
        main_module.app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["answer"], "คำตอบทดสอบ")
        self.assertEqual(payload["sources"], ["มาตรา 5"])
        self.assertEqual(payload["analysis"], "SUFFICIENT")


if __name__ == "__main__":
    unittest.main()
