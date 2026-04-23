import asyncio
import importlib
import json
import os
import shutil
import sqlite3
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from fastapi.testclient import TestClient

from app.core.errors import BadRequestError


@contextmanager
def workspace_tempdir():
    path = Path(".test-tmp") / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


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

        with workspace_tempdir() as tmpdir:
            doc_path = tmpdir / "พรบ.เเรงงาน.docx"
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
        self.assertIn("source_hash", chunks[2].metadata)
        self.assertIn("source_mtime", chunks[2].metadata)
        self.assertEqual(chunks[2].metadata["embedding_model"], module.settings.EMBED_MODEL_NAME)
        self.assertEqual(chunks[2].metadata["pipeline_version"], module.settings.VECTOR_PIPELINE_VERSION)
        self.assertEqual(chunks[2].metadata["chunk_index"], 2)


class KnowledgeBaseServiceTests(unittest.TestCase):
    def _make_document(self, tmpdir, relative_path, *, file_hash, file_mtime, collection_id="default"):
        from app.infrastructure.document_loader import DiscoveredDocument

        path = Path(tmpdir) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return DiscoveredDocument(
            path=path,
            relative_path=Path(relative_path).as_posix(),
            collection_id=collection_id,
            document_name=Path(relative_path).stem,
            file_mtime=file_mtime,
            file_hash=file_hash,
        )

    def _make_chunk(self, chunk_id, text, *, document, source_path, collection_id="default"):
        from app.domain.models import DocumentChunk
        from app.core.settings import settings

        return DocumentChunk(
            id=chunk_id,
            text=text,
            document=document,
            collection_id=collection_id,
            metadata={
                "document": document,
                "collection_id": collection_id,
                "chapter": "",
                "article": "",
                "source_path": source_path,
                "source_mtime": 1.0,
                "source_hash": f"hash-{chunk_id}",
                "embedding_model": settings.EMBED_MODEL_NAME,
                "pipeline_version": settings.VECTOR_PIPELINE_VERSION,
                "chunk_index": 0,
            },
        )

    def _make_loader(self, documents, chunks_by_source):
        class FakeLoader:
            def __init__(self, docs, source_chunks):
                self.documents = list(docs)
                self.chunks_by_source = {key: list(value) for key, value in source_chunks.items()}
                self.load_documents_calls = []

            def discover_documents(self):
                return list(self.documents)

            def load_documents(self, documents=None):
                docs = list(documents or self.documents)
                self.load_documents_calls.append([doc.relative_path for doc in docs])
                return {
                    doc.relative_path: list(self.chunks_by_source.get(doc.relative_path, []))
                    for doc in docs
                }

            def load(self):
                chunks = []
                for source_chunks in self.load_documents().values():
                    chunks.extend(source_chunks)
                return chunks

        return FakeLoader(documents, chunks_by_source)

    def _make_vector_store(self, initial_chunks=None):
        class FakeVectorStore:
            def __init__(self, starting_chunks):
                self.chunks = {chunk.id: chunk for chunk in (starting_chunks or [])}
                self.rebuild_calls = 0
                self.upsert_calls = []
                self.deleted_calls = []

            def rebuild(self, chunks):
                self.rebuild_calls += 1
                self.chunks = {chunk.id: chunk for chunk in chunks}

            def upsert_chunks(self, chunks):
                self.upsert_calls.append([chunk.id for chunk in chunks])
                for chunk in chunks:
                    self.chunks[chunk.id] = chunk
                return len(chunks)

            def delete_chunks(self, chunk_ids):
                self.deleted_calls.append(list(chunk_ids))
                for chunk_id in chunk_ids:
                    self.chunks.pop(chunk_id, None)
                return len(chunk_ids)

            def count(self):
                return len(self.chunks)

        return FakeVectorStore(initial_chunks)

    def _make_bm25(self):
        class FakeBM25Index:
            def __init__(self):
                self.rebuild_calls = 0
                self.last_chunks = []

            def rebuild(self, chunks):
                self.rebuild_calls += 1
                self.last_chunks = list(chunks)

        return FakeBM25Index()

    def test_incremental_sync_adds_only_new_chunks(self):
        from app.application.services.documents import KnowledgeBaseService

        with workspace_tempdir() as tmpdir:
            doc_a = self._make_document(tmpdir, "a.docx", file_hash="hash-a", file_mtime=1.0)
            chunk_a = self._make_chunk("chunk-a", "A", document="a", source_path="a.docx")
            loader = self._make_loader([doc_a], {"a.docx": [chunk_a]})
            vector_store = self._make_vector_store()
            bm25_index = self._make_bm25()
            service = KnowledgeBaseService(
                loader,
                vector_store,
                bm25_index,
                manifest_path=Path(tmpdir) / "manifest.json",
            )

            self.assertEqual(service.sync(), 1)

            doc_b = self._make_document(tmpdir, "b.docx", file_hash="hash-b", file_mtime=2.0)
            chunk_b = self._make_chunk("chunk-b", "B", document="b", source_path="b.docx")
            loader.documents = [doc_a, doc_b]
            loader.chunks_by_source["b.docx"] = [chunk_b]

            self.assertEqual(service.sync(), 2)

        self.assertEqual(vector_store.rebuild_calls, 1)
        self.assertEqual(vector_store.upsert_calls[-1], ["chunk-b"])
        self.assertEqual(bm25_index.last_chunks[-1].id, "chunk-b")

    def test_incremental_sync_replaces_changed_document_chunks(self):
        from app.application.services.documents import KnowledgeBaseService

        with workspace_tempdir() as tmpdir:
            doc_v1 = self._make_document(tmpdir, "labor.docx", file_hash="hash-v1", file_mtime=1.0)
            old_chunk = self._make_chunk("chunk-old", "old text", document="labor", source_path="labor.docx")
            loader = self._make_loader([doc_v1], {"labor.docx": [old_chunk]})
            vector_store = self._make_vector_store()
            bm25_index = self._make_bm25()
            service = KnowledgeBaseService(
                loader,
                vector_store,
                bm25_index,
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            service.sync()

            doc_v2 = self._make_document(tmpdir, "labor.docx", file_hash="hash-v2", file_mtime=2.0)
            new_chunk = self._make_chunk("chunk-new", "new text", document="labor", source_path="labor.docx")
            loader.documents = [doc_v2]
            loader.chunks_by_source["labor.docx"] = [new_chunk]

            self.assertEqual(service.sync(), 1)

        self.assertIn("chunk-old", vector_store.deleted_calls[-1])
        self.assertEqual(vector_store.upsert_calls[-1], ["chunk-new"])
        self.assertEqual([chunk.id for chunk in bm25_index.last_chunks], ["chunk-new"])

    def test_incremental_sync_removes_deleted_documents(self):
        from app.application.services.documents import KnowledgeBaseService

        with workspace_tempdir() as tmpdir:
            doc_a = self._make_document(tmpdir, "a.docx", file_hash="hash-a", file_mtime=1.0)
            doc_b = self._make_document(tmpdir, "b.docx", file_hash="hash-b", file_mtime=2.0)
            chunk_a = self._make_chunk("chunk-a", "A", document="a", source_path="a.docx")
            chunk_b = self._make_chunk("chunk-b", "B", document="b", source_path="b.docx")
            loader = self._make_loader([doc_a, doc_b], {"a.docx": [chunk_a], "b.docx": [chunk_b]})
            vector_store = self._make_vector_store()
            bm25_index = self._make_bm25()
            service = KnowledgeBaseService(
                loader,
                vector_store,
                bm25_index,
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            service.sync()

            loader.documents = [doc_a]
            loader.chunks_by_source.pop("b.docx")

            self.assertEqual(service.sync(), 1)

        self.assertIn("chunk-b", vector_store.deleted_calls[-1])
        self.assertEqual([chunk.id for chunk in bm25_index.last_chunks], ["chunk-a"])

    def test_incremental_sync_is_noop_when_documents_are_unchanged(self):
        from app.application.services.documents import KnowledgeBaseService

        with workspace_tempdir() as tmpdir:
            doc_a = self._make_document(tmpdir, "a.docx", file_hash="hash-a", file_mtime=1.0)
            chunk_a = self._make_chunk("chunk-a", "A", document="a", source_path="a.docx")
            loader = self._make_loader([doc_a], {"a.docx": [chunk_a]})
            vector_store = self._make_vector_store()
            bm25_index = self._make_bm25()
            service = KnowledgeBaseService(
                loader,
                vector_store,
                bm25_index,
                manifest_path=Path(tmpdir) / "manifest.json",
            )
            service.sync()
            vector_store.upsert_calls.clear()
            vector_store.deleted_calls.clear()

            self.assertEqual(service.sync(), 1)

        self.assertEqual(vector_store.upsert_calls[-1:], [])
        self.assertEqual(vector_store.deleted_calls[-1:], [[]])
        self.assertEqual([chunk.id for chunk in bm25_index.last_chunks], ["chunk-a"])

    def test_manifest_model_mismatch_forces_full_rebuild(self):
        from app.application.services.documents import KnowledgeBaseService

        with workspace_tempdir() as tmpdir:
            manifest_path = tmpdir / "manifest.json"
            doc_a = self._make_document(tmpdir, "a.docx", file_hash="hash-a", file_mtime=1.0)
            chunk_a = self._make_chunk("chunk-a", "A", document="a", source_path="a.docx")
            loader = self._make_loader([doc_a], {"a.docx": [chunk_a]})
            vector_store = self._make_vector_store()
            bm25_index = self._make_bm25()
            service = KnowledgeBaseService(loader, vector_store, bm25_index, manifest_path=manifest_path)
            service.sync()

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["embedding_model"] = "different-model"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            reloaded_service = KnowledgeBaseService(loader, vector_store, bm25_index, manifest_path=manifest_path)
            self.assertEqual(reloaded_service.sync(), 1)

        self.assertEqual(vector_store.rebuild_calls, 2)


class ChromaVectorStoreTests(unittest.TestCase):
    def _make_chunk(self, chunk_id, text):
        from app.domain.models import DocumentChunk

        return DocumentChunk(
            id=chunk_id,
            text=text,
            document="labor",
            collection_id="default",
            article="มาตรา ๓๒",
            metadata={"source_path": "labor.docx", "chunk_index": 0},
        )

    def test_rebuild_clears_existing_ids_without_recreating_collection(self):
        from app.infrastructure.vectorstores.chroma_store import ChromaVectorStore

        class FakeClient:
            def delete_collection(self, name):
                raise AssertionError(f"rebuild should not delete collection {name}")

        class FakeCollection:
            def __init__(self):
                self.ids = ["old-1", "old-2"]
                self.deleted_ids = []
                self.upserted_ids = []

            def get(self, include=None):
                return {"ids": list(self.ids)}

            def delete(self, ids):
                self.deleted_ids.extend(ids)
                self.ids = [item for item in self.ids if item not in ids]

            def upsert(self, *, documents, metadatas, ids):
                self.upserted_ids.extend(ids)
                self.ids.extend(ids)

        collection = FakeCollection()
        store = ChromaVectorStore.__new__(ChromaVectorStore)
        store.client = FakeClient()
        store.collection = collection

        store.rebuild([self._make_chunk("new-1", "ลาป่วยได้เท่าที่ป่วยจริง")])

        self.assertEqual(collection.deleted_ids, ["old-1", "old-2"])
        self.assertEqual(collection.upserted_ids, ["new-1"])
        self.assertEqual(collection.ids, ["new-1"])

    def test_embedding_function_wraps_single_query_vector_for_chroma(self):
        from app.infrastructure.vectorstores.chroma_store import ThaiLegalEmbeddingFunction

        class FakeModel:
            def encode(self, texts, show_progress_bar=False):
                self.texts = texts
                return [0.1, 0.2, 0.3]

        embedding = ThaiLegalEmbeddingFunction.__new__(ThaiLegalEmbeddingFunction)
        embedding.model = FakeModel()

        vectors = [list(vector) for vector in embedding(["ลาป่วยได้กี่วัน"])]
        self.assertEqual(vectors, [[0.1, 0.2, 0.3]])

    def test_search_sends_explicit_query_embedding_matrix(self):
        from app.infrastructure.vectorstores.chroma_store import ChromaVectorStore

        class FakeEmbedding:
            def __call__(self, input):
                return [[0.1, 0.2, 0.3]]

        class FakeCollection:
            def __init__(self):
                self.query_kwargs = None

            def count(self):
                return 1

            def query(self, **kwargs):
                self.query_kwargs = kwargs
                return {
                    "documents": [["มาตรา ๓๒ ให้ลูกจ้างมีสิทธิลาป่วยได้เท่าที่ป่วยจริง"]],
                    "metadatas": [[{"document": "labor", "collection_id": "default", "article": "มาตรา ๓๒"}]],
                    "ids": [["chunk-32"]],
                    "distances": [[0.25]],
                }

        collection = FakeCollection()
        store = ChromaVectorStore.__new__(ChromaVectorStore)
        store.collection = collection
        store.embedding_fn = FakeEmbedding()

        results = store.search("ลาป่วยได้กี่วัน", n_results=1)

        self.assertNotIn("query_texts", collection.query_kwargs)
        self.assertEqual(collection.query_kwargs["query_embeddings"], [[0.1, 0.2, 0.3]])
        self.assertEqual(results[0].chunk_id, "chunk-32")


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

        with workspace_tempdir() as tmpdir:
            db_path = tmpdir / "threads.db"
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

    def test_init_db_migrates_existing_messages_table_without_source_items(self):
        from app.infrastructure.repositories.thread_repository import SQLiteThreadRepository

        with workspace_tempdir() as tmpdir:
            db_path = tmpdir / "threads.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE threads (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT,
                    role TEXT,
                    content TEXT,
                    sources TEXT,
                    needs_clarification BOOLEAN,
                    created_at TEXT,
                    FOREIGN KEY (thread_id) REFERENCES threads (id)
                )
                """
            )
            conn.commit()
            conn.close()

            repo = SQLiteThreadRepository(db_path)
            repo.init_db()

            migrated_conn = sqlite3.connect(db_path)
            columns = [row[1] for row in migrated_conn.execute("PRAGMA table_info(messages)").fetchall()]
            migrated_conn.close()

            self.assertIn("source_items", columns)

            thread_id = repo.create_thread("ทดสอบ")
            repo.add_message(thread_id, "user", "คำถาม")
            messages = repo.get_thread_messages(thread_id)

        self.assertEqual(messages[0].source_items, [])


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

    def test_streaming_returns_public_app_error_message(self):
        main_module = importlib.import_module("app.main")
        dependencies_module = importlib.import_module("app.dependencies")
        client = TestClient(main_module.app)

        class ExplodingGraph:
            async def astream_events(self, *_args, **_kwargs):
                raise BadRequestError("Model 'claude-3-sonnet-20240229' is not supported by this backend.")
                yield

        class FakeStreamUseCase:
            def __init__(self):
                self.graph = ExplodingGraph()

            async def start(self, request):
                return "thread-1", {"query": request.query}

        main_module.app.dependency_overrides[dependencies_module.get_stream_answer_use_case] = lambda: FakeStreamUseCase()

        with client.stream("POST", "/api/v1/ask/stream", json={"query": "hello"}) as response:
            chunks = list(response.iter_text())

        main_module.app.dependency_overrides.clear()

        stream_text = "".join(chunks)
        self.assertIn("is not supported by this backend", stream_text)
        self.assertNotIn("Streaming failed.", stream_text)


if __name__ == "__main__":
    unittest.main()
