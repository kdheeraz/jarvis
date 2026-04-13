import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy.orm import Session

from app.config import get_config
from app.db.models import Document
from app.rag.factory import get_vectorstore
from app.rag.ingestion.loaders import load_document
from app.rag.ingestion.splitters import get_text_splitter

UPLOAD_DIR = Path("./data/uploads")


def ingest_file(db: Session, file_path: str, filename: str, collection_name: str) -> str:
    """Ingest a single file into the vector store. Returns document ID."""
    doc_id = str(uuid.uuid4())
    file_size = os.path.getsize(file_path)
    file_type = Path(filename).suffix.lower()

    # Create tracking record
    doc_record = Document(
        id=doc_id,
        collection_name=collection_name,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        status="processing",
    )
    db.add(doc_record)
    db.commit()

    try:
        # Load document
        documents = load_document(file_path)
        logger.info(f"Loaded {len(documents)} pages from {filename}")

        # Split into chunks
        splitter = get_text_splitter()
        chunks = splitter.split_documents(documents)
        logger.info(f"Split into {len(chunks)} chunks")

        # Add metadata
        for chunk in chunks:
            chunk.metadata["source"] = filename
            chunk.metadata["collection"] = collection_name
            chunk.metadata["document_id"] = doc_id

        # Add to vector store
        vectorstore = get_vectorstore()
        if vectorstore is None:
            raise RuntimeError("Vector store is not configured or RAG is disabled")

        vectorstore.add_documents(chunks)
        logger.info(f"Added {len(chunks)} chunks to vector store")

        # Update tracking
        doc_record.status = "complete"
        doc_record.chunk_count = len(chunks)
        doc_record.completed_at = datetime.now(timezone.utc)
        db.commit()

        return doc_id

    except Exception as e:
        logger.error(f"Ingestion failed for {filename}: {e}")
        doc_record.status = "failed"
        doc_record.error_message = str(e)
        db.commit()
        raise


def save_upload(file_content: bytes, filename: str) -> str:
    """Save uploaded file to disk and return the path."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{filename}"
    with open(file_path, "wb") as f:
        f.write(file_content)
    return str(file_path)
