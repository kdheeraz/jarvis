from pathlib import Path

from langchain_core.documents import Document
from loguru import logger


def load_document(file_path: str) -> list[Document]:
    """Load a document from file path using the appropriate loader."""
    ext = Path(file_path).suffix.lower()
    logger.debug(f"Loading document: {file_path} (type={ext})")

    if ext == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader
        return PyPDFLoader(file_path).load()

    elif ext in (".docx", ".doc"):
        from langchain_community.document_loaders import Docx2txtLoader
        return Docx2txtLoader(file_path).load()

    elif ext == ".csv":
        from langchain_community.document_loaders import CSVLoader
        return CSVLoader(file_path).load()

    elif ext in (".html", ".htm"):
        from langchain_community.document_loaders import UnstructuredHTMLLoader
        return UnstructuredHTMLLoader(file_path).load()

    elif ext == ".txt":
        from langchain_community.document_loaders import TextLoader
        return TextLoader(file_path).load()

    elif ext in (".md", ".markdown"):
        from langchain_community.document_loaders import UnstructuredMarkdownLoader
        return UnstructuredMarkdownLoader(file_path).load()

    elif ext in (".json", ".jsonl"):
        from langchain_community.document_loaders import JSONLoader
        return JSONLoader(file_path, jq_schema=".", text_content=False).load()

    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
        from langchain_community.document_loaders import UnstructuredImageLoader
        return UnstructuredImageLoader(file_path).load()

    elif ext in (".pptx", ".ppt"):
        from langchain_community.document_loaders import UnstructuredPowerPointLoader
        return UnstructuredPowerPointLoader(file_path).load()

    elif ext in (".xlsx", ".xls"):
        from langchain_community.document_loaders import UnstructuredExcelLoader
        return UnstructuredExcelLoader(file_path).load()

    else:
        # Fallback: try as plain text
        logger.warning(f"Unknown file type {ext}, trying as text")
        from langchain_community.document_loaders import TextLoader
        return TextLoader(file_path).load()
