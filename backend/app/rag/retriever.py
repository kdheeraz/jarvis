from typing import Optional

from langchain_core.retrievers import BaseRetriever
from loguru import logger

from app.config import get_config
from app.rag.factory import get_vectorstore


def get_retriever() -> Optional[BaseRetriever]:
    """Get the active RAG retriever. Returns None if RAG is disabled."""
    config = get_config()
    if not config.rag.enabled:
        return None

    vectorstore = get_vectorstore()
    if vectorstore is None:
        logger.warning("RAG enabled but vector store not available")
        return None

    return vectorstore.as_retriever(search_kwargs={"k": 4})
