from typing import List, Dict, Any
from pathlib import Path
import fitz  # PyMuPDF


class DocumentExtractor:
    """Extracts text content page-by-page from PDF and text documents."""

    @staticmethod
    def extract_pages(file_path: Path) -> List[Dict[str, Any]]:
        """
        Extracts pages/content from a PDF or text file.

        Returns a list of dicts with keys:
            - page_number: 1-indexed integer
            - text: extracted text string
            - document_name: filename
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found at: {file_path}")

        doc_name = file_path.name
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            pages_data = []
            doc = fitz.open(file_path)
            try:
                for page_idx in range(len(doc)):
                    page = doc[page_idx]
                    text = page.get_text()
                    if text.strip():
                        pages_data.append({
                            "page_number": page_idx + 1,
                            "text": text,
                            "document_name": doc_name
                        })
            finally:
                doc.close()
            return pages_data

        elif suffix in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if content.strip():
                return [{
                    "page_number": 1,
                    "text": content,
                    "document_name": doc_name
                }]
            return []
        else:
            raise ValueError(f"Unsupported file format: {suffix}")


PDFExtractor = DocumentExtractor

