import shutil
from pathlib import Path

from fastapi import UploadFile

from app.core.errors import BadRequestError, NotFoundError
from app.core.settings import settings
from app.domain.models import CollectionInfo


class KnowledgeBaseService:
    def __init__(self, document_loader, vector_store, bm25_index):
        self.document_loader = document_loader
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self._chunks = []

    def sync(self, *, force: bool = True) -> int:
        chunks = self.document_loader.load()
        if force or self.vector_store.count() == 0:
            self.vector_store.rebuild(chunks)
        self.bm25_index.rebuild(chunks)
        self._chunks = chunks
        return len(chunks)

    def ensure_ready(self) -> int:
        if self._chunks:
            return len(self._chunks)
        if self.vector_store.count() == 0:
            return self.sync(force=True)
        self._chunks = self.document_loader.load()
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
