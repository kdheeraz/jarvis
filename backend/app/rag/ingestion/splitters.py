from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_config


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    config = get_config()
    return RecursiveCharacterTextSplitter(
        chunk_size=config.rag.chunk_size,
        chunk_overlap=config.rag.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
