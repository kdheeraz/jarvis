from typing import Optional

from langchain_core.vectorstores import VectorStore
from loguru import logger

from app.config import JarvisConfig, get_config


def create_vectorstore(config: JarvisConfig | None = None) -> Optional[VectorStore]:
    """Create the active vector store based on config."""
    if config is None:
        config = get_config()

    if not config.rag.enabled:
        return None

    embeddings = _create_embeddings(config)
    store_type = config.rag.store
    logger.info(f"Creating vector store: {store_type}")

    if store_type == "chromadb":
        return _create_chroma(config, embeddings)
    elif store_type == "faiss":
        return _create_faiss(config, embeddings)
    elif store_type == "opensearch":
        return _create_opensearch(config, embeddings)
    elif store_type == "pgvector":
        return _create_pgvector(config, embeddings)
    else:
        raise ValueError(f"Unknown vector store: {store_type}")


def _create_embeddings(config: JarvisConfig):
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=config.rag.embedding_model)


def _create_chroma(config: JarvisConfig, embeddings):
    from langchain_chroma import Chroma
    import chromadb

    client = chromadb.HttpClient(
        host=config.rag.chromadb.host,
        port=config.rag.chromadb.port,
    )
    return Chroma(
        client=client,
        collection_name="jarvis_default",
        embedding_function=embeddings,
    )


def _create_faiss(config: JarvisConfig, embeddings):
    from langchain_community.vectorstores import FAISS
    from pathlib import Path

    index_path = Path(config.rag.faiss.index_path)
    if index_path.exists():
        return FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
    else:
        # Create empty FAISS index — will be populated during ingestion
        return FAISS.from_texts(["initialization"], embeddings)


def _create_opensearch(config: JarvisConfig, embeddings):
    from langchain_community.vectorstores import OpenSearchVectorSearch

    return OpenSearchVectorSearch(
        opensearch_url=f"http://{config.rag.opensearch.host}:{config.rag.opensearch.port}",
        index_name="jarvis_default",
        embedding_function=embeddings,
    )


def _create_pgvector(config: JarvisConfig, embeddings):
    from langchain_community.vectorstores import PGVector

    return PGVector(
        connection_string=config.rag.pgvector.connection_string,
        collection_name="jarvis_default",
        embedding_function=embeddings,
    )


# Singleton
_vectorstore: Optional[VectorStore] = None


def get_vectorstore() -> Optional[VectorStore]:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = create_vectorstore()
    return _vectorstore


def reset_vectorstore():
    global _vectorstore
    _vectorstore = None
