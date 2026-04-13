from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from loguru import logger
from sqlalchemy.orm import Session

from app.auth.middleware import require_admin
from app.db.engine import get_db, get_session_factory
from app.db.models import Collection, Document
from app.rag.ingestion.pipeline import ingest_file, save_upload
from app.schemas.rag import CollectionCreate, CollectionOut, DocumentOut

router = APIRouter(prefix="/api/admin/rag", tags=["admin-rag"], dependencies=[Depends(require_admin)])


def _run_ingestion(file_path: str, filename: str, collection_name: str):
    """Run ingestion in background with its own DB session."""
    factory = get_session_factory()
    db = factory()
    try:
        ingest_file(db, file_path, filename, collection_name)
    except Exception as e:
        logger.error(f"Background ingestion failed for {filename}: {e}")
    finally:
        db.close()


@router.get("/collections", response_model=list[CollectionOut], response_model_by_alias=True)
def list_collections(db: Session = Depends(get_db)):
    # Get all registered collections
    registered = {c.name for c in db.query(Collection).all()}

    # Also get collections that have documents but weren't explicitly created
    doc_colls = db.query(Document.collection_name).distinct().all()
    all_names = registered | {name for (name,) in doc_colls}

    collections = []
    for name in sorted(all_names):
        count = db.query(Document).filter(
            Document.collection_name == name,
            Document.status == "complete",
        ).count()
        collections.append(CollectionOut(name=name, doc_count=count))
    return collections


@router.post("/collections", response_model=CollectionOut, response_model_by_alias=True, status_code=201)
def create_collection(request: CollectionCreate, db: Session = Depends(get_db)):
    existing = db.query(Collection).filter(Collection.name == request.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Collection '{request.name}' already exists")
    db.add(Collection(name=request.name))
    db.commit()
    return CollectionOut(name=request.name, doc_count=0)


@router.delete("/collections/{name}", status_code=204)
def delete_collection(name: str, db: Session = Depends(get_db)):
    db.query(Document).filter(Document.collection_name == name).delete()
    db.query(Collection).filter(Collection.name == name).delete()
    db.commit()


@router.post("/ingest")
async def ingest_files(
    collection_name: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    # Auto-register collection if not exists
    if not db.query(Collection).filter(Collection.name == collection_name).first():
        db.add(Collection(name=collection_name))
        db.commit()

    filenames = []
    for file in files:
        content = await file.read()
        file_path = save_upload(content, file.filename)
        background_tasks.add_task(_run_ingestion, file_path, file.filename, collection_name)
        filenames.append(file.filename)

    return {
        "status": "accepted",
        "message": f"Queued {len(files)} files for ingestion into '{collection_name}'",
        "files": filenames,
    }


@router.get("/documents", response_model=list[DocumentOut], response_model_by_alias=True)
def list_documents(
    collection_name: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if collection_name:
        query = query.filter(Document.collection_name == collection_name)
    return query.order_by(Document.created_at.desc()).limit(100).all()
