import os
import re
from typing import List


class DocumentLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.law_name = os.path.basename(file_path).replace(".docx", "")

    def load(self) -> List[str]:
        import docx

        doc = docx.Document(self.file_path)
        chunks: list[str] = []
        current_chapter = ""
        current_article = "บททั่วไป/คำปรารภ"

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            match_chapter = re.match(r"^(หมวด\s*[๐-๙0-9]+\s*.*)", text)
            if match_chapter:
                current_chapter = match_chapter.group(1).strip()
                chunks.append(f"[{self.law_name}] {text}")
                continue

            match_article = re.match(r"^((?:มาตรา|ข้อ)\s*[๐-๙0-9/]+)", text)
            if match_article:
                current_article = match_article.group(1).strip()
                tag = f"[{self.law_name}]"
                if current_chapter:
                    tag += f" [{current_chapter}]"
                chunks.append(f"{tag} {text}")
                continue

            tag = f"[{self.law_name}]"
            if current_chapter:
                tag += f" [{current_chapter}]"
            tag += f" [{current_article}]"
            chunks.append(f"{tag} {text}")

        return chunks

