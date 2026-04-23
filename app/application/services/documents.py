import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.core.logging import logger
from app.core.errors import BadRequestError, NotFoundError
from app.core.settings import settings
from app.domain.models import CollectionInfo
from app.infrastructure.document_loader import DiscoveredDocument


class KnowledgeBaseService:
    def __init__(self, document_loader, vector_store, bm25_index, manifest_path: Path | None = None):
        self.document_loader = document_loader
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.manifest_path = manifest_path or Path(settings.CHROMA_DB_DIR) / "knowledge_base_manifest.json"
        self._chunks = []
        self._last_sync_summary: dict[str, Any] | None = None

    @staticmethod
    def _normalize_relative_paths(relative_paths: list[str] | None) -> set[str]:
        return {Path(path).as_posix() for path in (relative_paths or []) if path}

    @staticmethod
    def _flatten_chunks(chunks_by_source: dict[str, list]) -> list:
        flattened = []
        for source_path in sorted(chunks_by_source):
            flattened.extend(chunks_by_source[source_path])
        return flattened

    @staticmethod
    def _chunk_count_from_documents(document_entries: dict[str, dict[str, Any]]) -> int:
        return sum(len(entry.get("chunk_ids", [])) for entry in document_entries.values())

    def _build_manifest_entry(self, document: DiscoveredDocument, chunks: list) -> dict[str, Any]:
        return {
            "relative_path": document.relative_path,
            "collection_id": document.collection_id,
            "document_name": document.document_name,
            "file_mtime": document.file_mtime,
            "file_hash": document.file_hash,
            "chunk_ids": [chunk.id for chunk in chunks],
            "embedding_model": settings.EMBED_MODEL_NAME,
            "pipeline_version": settings.VECTOR_PIPELINE_VERSION,
        }

    def _build_manifest_payload(
        self,
        *,
        documents: dict[str, dict[str, Any]],
        chunks: list,
    ) -> dict[str, Any]:
        return {
            "embedding_model": settings.EMBED_MODEL_NAME,
            "pipeline_version": settings.VECTOR_PIPELINE_VERSION,
            "documents": documents,
            "chunks": [chunk.model_dump() for chunk in chunks],
        }

    def _save_manifest(self, *, documents: dict[str, dict[str, Any]], chunks: list) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._build_manifest_payload(documents=documents, chunks=chunks)
        self.manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_manifest(self) -> tuple[dict[str, Any] | None, str | None]:
        if not self.manifest_path.exists():
            return None, "manifest_missing"

        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to read knowledge base manifest from %s", self.manifest_path)
            return None, "manifest_invalid"

        if payload.get("embedding_model") != settings.EMBED_MODEL_NAME:
            return None, "embedding_model_changed"
        if payload.get("pipeline_version") != settings.VECTOR_PIPELINE_VERSION:
            return None, "pipeline_version_changed"

        documents = payload.get("documents")
        chunk_payloads = payload.get("chunks")
        if not isinstance(documents, dict) or not isinstance(chunk_payloads, list):
            return None, "manifest_invalid"

        chunk_ids = {chunk.get("id") for chunk in chunk_payloads if isinstance(chunk, dict)}
        for relative_path, entry in documents.items():
            if not isinstance(entry, dict):
                return None, "manifest_invalid"
            entry_chunk_ids = entry.get("chunk_ids")
            if not isinstance(entry_chunk_ids, list):
                return None, "manifest_invalid"
            if any(chunk_id not in chunk_ids for chunk_id in entry_chunk_ids):
                logger.warning("Manifest entry %s references unknown chunk ids. Forcing rebuild.", relative_path)
                return None, "manifest_invalid"

        return payload, None

    def _load_manifest_chunks(self, manifest: dict[str, Any]) -> list:
        from app.domain.models import DocumentChunk

        return [DocumentChunk.model_validate(chunk) for chunk in manifest.get("chunks", [])]

    @staticmethod
    def _document_changed(document: DiscoveredDocument, entry: dict[str, Any]) -> bool:
        return (
            entry.get("file_hash") != document.file_hash
            or float(entry.get("file_mtime", 0.0)) != float(document.file_mtime)
            or entry.get("collection_id") != document.collection_id
            or entry.get("document_name") != document.document_name
        )

    def _sync_incremental(
        self,
        *,
        manifest: dict[str, Any],
        current_documents: dict[str, DiscoveredDocument],
        target_paths: set[str],
    ) -> dict[str, Any]:
        previous_documents: dict[str, dict[str, Any]] = dict(manifest["documents"])
        snapshot_chunks = self._load_manifest_chunks(manifest)
        snapshot_by_id = {chunk.id: chunk for chunk in snapshot_chunks}

        if target_paths:
            relevant_current = {path: doc for path, doc in current_documents.items() if path in target_paths}
            relevant_previous = {path: entry for path, entry in previous_documents.items() if path in target_paths}
        else:
            relevant_current = current_documents
            relevant_previous = previous_documents

        added = sorted(set(relevant_current) - set(relevant_previous))
        deleted = sorted(set(relevant_previous) - set(relevant_current))
        changed = sorted(
            path
            for path in set(relevant_current).intersection(relevant_previous)
            if self._document_changed(relevant_current[path], relevant_previous[path])
        )

        chunk_ids_to_delete = []
        for path in [*deleted, *changed]:
            chunk_ids_to_delete.extend(previous_documents[path].get("chunk_ids", []))

        deleted_chunks = self.vector_store.delete_chunks(chunk_ids_to_delete)
        for chunk_id in chunk_ids_to_delete:
            snapshot_by_id.pop(chunk_id, None)

        documents_to_load = [current_documents[path] for path in [*added, *changed]]
        new_chunks_by_source = self.document_loader.load_documents(documents_to_load) if documents_to_load else {}
        new_chunks = self._flatten_chunks(new_chunks_by_source)
        upserted_chunks = self.vector_store.upsert_chunks(new_chunks) if new_chunks else 0

        for path in deleted:
            previous_documents.pop(path, None)

        for path in [*added, *changed]:
            source_chunks = new_chunks_by_source.get(path, [])
            for chunk in source_chunks:
                snapshot_by_id[chunk.id] = chunk
            previous_documents[path] = self._build_manifest_entry(current_documents[path], source_chunks)

        snapshot = sorted(snapshot_by_id.values(), key=lambda chunk: chunk.id)
        self.bm25_index.rebuild(snapshot)
        self._chunks = snapshot
        self._save_manifest(documents=previous_documents, chunks=snapshot)

        summary = {
            "mode": "incremental",
            "full_rebuild": False,
            "reason": None,
            "added": len(added),
            "changed": len(changed),
            "deleted": len(deleted),
            "upserted_chunks": upserted_chunks,
            "deleted_chunks": deleted_chunks,
            "chunk_count": len(snapshot),
        }
        logger.info(
            "Knowledge base incremental sync completed: added=%s changed=%s deleted=%s upserted_chunks=%s deleted_chunks=%s total_chunks=%s",
            summary["added"],
            summary["changed"],
            summary["deleted"],
            summary["upserted_chunks"],
            summary["deleted_chunks"],
            summary["chunk_count"],
        )
        return summary

    def _full_rebuild(self, *, current_documents: dict[str, DiscoveredDocument], reason: str) -> dict[str, Any]:
        previous_chunk_count = self.vector_store.count()
        discovered_documents = [current_documents[path] for path in sorted(current_documents)]
        chunks_by_source = self.document_loader.load_documents(discovered_documents)
        chunks = self._flatten_chunks(chunks_by_source)
        self.vector_store.rebuild(chunks)
        self.bm25_index.rebuild(chunks)
        self._chunks = chunks

        manifest_documents = {
            document.relative_path: self._build_manifest_entry(
                document,
                chunks_by_source.get(document.relative_path, []),
            )
            for document in discovered_documents
        }
        self._save_manifest(documents=manifest_documents, chunks=chunks)

        summary = {
            "mode": "rebuild",
            "full_rebuild": True,
            "reason": reason,
            "added": len(discovered_documents),
            "changed": 0,
            "deleted": 0,
            "upserted_chunks": len(chunks),
            "deleted_chunks": previous_chunk_count,
            "chunk_count": len(chunks),
        }
        logger.info(
            "Knowledge base full rebuild completed: reason=%s documents=%s total_chunks=%s",
            reason,
            len(discovered_documents),
            len(chunks),
        )
        return summary

    def synchronize(self, *, force: bool = False, relative_paths: list[str] | None = None) -> dict[str, Any]:
        current_documents = {
            document.relative_path: document for document in self.document_loader.discover_documents()
        }
        target_paths = self._normalize_relative_paths(relative_paths)
        manifest, manifest_error = self._load_manifest()

        rebuild_reason = None
        if force:
            rebuild_reason = "force_requested"
        elif manifest is None:
            if manifest_error in {"embedding_model_changed", "pipeline_version_changed", "manifest_invalid"}:
                rebuild_reason = manifest_error
            elif self.vector_store.count() > 0:
                rebuild_reason = manifest_error or "manifest_missing"
        elif self.vector_store.count() == 0 and self._chunk_count_from_documents(manifest["documents"]) > 0:
            rebuild_reason = "vector_store_empty"

        if rebuild_reason:
            summary = self._full_rebuild(current_documents=current_documents, reason=rebuild_reason)
        elif manifest is None:
            summary = self._full_rebuild(current_documents=current_documents, reason="initial_sync")
        else:
            summary = self._sync_incremental(
                manifest=manifest,
                current_documents=current_documents,
                target_paths=target_paths,
            )

        self._last_sync_summary = summary
        return summary

    def sync(self, *, force: bool = False, relative_paths: list[str] | None = None) -> int:
        return int(self.synchronize(force=force, relative_paths=relative_paths)["chunk_count"])

    def ensure_ready(self) -> int:
        if self._chunks:
            return len(self._chunks)

        manifest, manifest_error = self._load_manifest()
        if self.vector_store.count() == 0:
            return self.sync(force=True)

        if manifest is None:
            logger.info(
                "Knowledge base manifest unavailable during ensure_ready (%s). Falling back to full rebuild.",
                manifest_error or "unknown",
            )
            return self.sync(force=True)

        self._chunks = self._load_manifest_chunks(manifest)
        self.bm25_index.rebuild(self._chunks)
        return len(self._chunks)

    def get_collections(self) -> list[CollectionInfo]:
        self.ensure_ready()
        counts: dict[str, set[str]] = {}
        for chunk in self._chunks:
            counts.setdefault(chunk.collection_id, set()).add(chunk.document)
        return [
            CollectionInfo(id=collection_id, name=collection_id, document_count=len(documents))
            for collection_id, documents in sorted(counts.items())
        ]


class DocumentService:
    def __init__(self, base_path: Path):
        self.base_path = base_path

    def _collection_dir(self, collection_id: str | None) -> Path:
        if not collection_id or collection_id == settings.DEFAULT_COLLECTION_ID:
            return self.base_path
        return self.base_path / collection_id

    def list_documents(self) -> list[dict]:
        if not self.base_path.exists():
            return []

        files = []
        for file_path in sorted(self.base_path.rglob("*.docx")):
            stats = file_path.stat()
            try:
                relative_path = file_path.relative_to(self.base_path)
            except ValueError:
                relative_path = Path(file_path.name)

            collection_id = (
                relative_path.parts[0] if len(relative_path.parts) > 1 else settings.DEFAULT_COLLECTION_ID
            )
            files.append(
                {
                    "name": file_path.name,
                    "size": stats.st_size,
                    "modified": stats.st_mtime,
                    "collection_id": collection_id,
                    "relative_path": relative_path.as_posix(),
                }
            )
        return files

    async def upload_documents(
        self,
        files: list[UploadFile],
        *,
        collection_id: str | None = None,
    ) -> list[str]:
        target_dir = self._collection_dir(collection_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = []
        for file in files:
            if not file.filename or not file.filename.endswith(".docx"):
                continue
            file_path = target_dir / Path(file.filename).name
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_files.append(file_path.name)
        return uploaded_files

    def delete_document(self, filename: str) -> str:
        if "/" in filename or "\\" in filename:
            candidate = (self.base_path / filename).resolve()
            if not str(candidate).startswith(str(self.base_path.resolve())):
                raise BadRequestError("Invalid document path.")
            file_path = candidate
        else:
            matches = list(self.base_path.rglob(filename))
            if not matches:
                raise NotFoundError("File not found.")
            file_path = matches[0]

        if not file_path.exists():
            raise NotFoundError("File not found.")

        file_path.unlink()
        return file_path.name
