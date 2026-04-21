import os
import re
from pathlib import Path
from typing import Any, Dict, List


class DocumentLoader:
    def __init__(self, target_path: str):
        self.target_path = Path(target_path)

    def load(self) -> List[Dict[str, Any]]:
        import docx

        chunks: List[Dict[str, Any]] = []
        files_to_process = []
        
        if self.target_path.is_file() and self.target_path.suffix == ".docx":
            files_to_process = [self.target_path]
        elif self.target_path.is_dir():
            files_to_process = list(self.target_path.glob("*.docx"))

        for file_path in files_to_process:
            law_name = file_path.name.replace(".docx", "")
            doc = docx.Document(str(file_path))
            current_chapter = ""
            current_article = "บททั่วไป/คำปรารภ"

            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue

                match_chapter = re.match(r"^(หมวด\s*[๐-๙0-9]+\s*.*)", text)
                if match_chapter:
                    current_chapter = match_chapter.group(1).strip()
                    chunks.append({
                        "text": f"[{law_name}] {text}",
                        "metadata": {"document": law_name}
                    })
                    continue

                match_article = re.match(r"^((?:มาตรา|ข้อ)\s*[๐-๙0-9/]+)", text)
                if match_article:
                    current_article = match_article.group(1).strip()
                    tag = f"[{law_name}]"
                    if current_chapter:
                        tag += f" [{current_chapter}]"
                    chunks.append({
                        "text": f"{tag} {text}",
                        "metadata": {"document": law_name}
                    })
                    continue

                tag = f"[{law_name}]"
                if current_chapter:
                    tag += f" [{current_chapter}]"
                tag += f" [{current_article}]"
                chunks.append({
                    "text": f"{tag} {text}",
                    "metadata": {"document": law_name}
                })

        return chunks

