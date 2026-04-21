import hashlib
import re
from pathlib import Path

from app.core.settings import settings
from app.domain.models import DocumentChunk


def _normalize_identifier(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9ก-๙]+", "-", value.strip()).strip("-").lower()
    return normalized or settings.DEFAULT_COLLECTION_ID


class DocumentLoader:
    def __init__(self, target_path: str):
        self.target_path = Path(target_path)

    def _resolve_collection_id(self, file_path: Path) -> str:
        base_dir = self.target_path if self.target_path.is_dir() else settings.resolved_doc_path

        try:
            relative_parent = file_path.parent.relative_to(base_dir)
        except ValueError:
            return settings.DEFAULT_COLLECTION_ID

        if not relative_parent.parts:
            return settings.DEFAULT_COLLECTION_ID

        return _normalize_identifier("__".join(relative_parent.parts))

    def _build_chunk_id(
        self,
        collection_id: str,
        document: str,
        chapter: str | None,
        article: str | None,
        index: int,
        text: str,
    ) -> str:
        identity = "|".join([collection_id, document, chapter or "", article or "", str(index), text])
        return hashlib.sha1(identity.encode("utf-8")).hexdigest()

    def load(self) -> list[DocumentChunk]:
        import docx

        chunks: list[DocumentChunk] = []
        files_to_process: list[Path] = []

        if self.target_path.is_file() and self.target_path.suffix == ".docx":
            files_to_process = [self.target_path]
        elif self.target_path.is_dir():
            files_to_process = sorted(self.target_path.rglob("*.docx"))

        for file_path in files_to_process:
            law_name = file_path.stem
            collection_id = self._resolve_collection_id(file_path)
            doc = docx.Document(str(file_path))
            current_chapter = ""
            current_article = "บททั่วไป/คำปรารภ"
            relative_path = str(file_path.relative_to(settings.resolved_doc_path)) if file_path.is_relative_to(settings.resolved_doc_path) else file_path.name

            for index, para in enumerate(doc.paragraphs):
                text = para.text.strip()
                if not text:
                    continue

                match_chapter = re.match(r"^(หมวด\s*[๐-๙0-9]+\s*.*)", text)
                if match_chapter:
                    current_chapter = match_chapter.group(1).strip()
                    chunk_text = f"[{law_name}] {text}"
                    chapter = current_chapter
                    article = None
                else:
                    match_article = re.match(r"^((?:มาตรา|ข้อ)\s*[๐-๙0-9/]+)", text)
                    if match_article:
                        current_article = match_article.group(1).strip()
                        tag = f"[{law_name}]"
                        if current_chapter:
                            tag += f" [{current_chapter}]"
                        chunk_text = f"{tag} {text}"
                        chapter = current_chapter or None
                        article = current_article
                    else:
                        tag = f"[{law_name}]"
                        if current_chapter:
                            tag += f" [{current_chapter}]"
                        tag += f" [{current_article}]"
                        chunk_text = f"{tag} {text}"
                        chapter = current_chapter or None
                        article = current_article

                chunks.append(
                    DocumentChunk(
                        id=self._build_chunk_id(collection_id, law_name, chapter, article, index, chunk_text),
                        text=chunk_text,
                        document=law_name,
                        collection_id=collection_id,
                        chapter=chapter,
                        article=article,
                        metadata={
                            "document": law_name,
                            "collection_id": collection_id,
                            "chapter": chapter or "",
                            "article": article or "",
                            "source_path": relative_path,
                        },
                    )
                )

        return chunks
