from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


def _to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class CollectionOut(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    name: str
    doc_count: int = 0


class CollectionCreate(BaseModel):
    name: str


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=_to_camel, populate_by_name=True)

    id: str
    collection_name: str
    filename: str
    file_type: str
    file_size: Optional[int] = None
    chunk_count: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class IngestionStatusOut(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    job_id: str
    status: str
    progress: Optional[int] = None
    errors: Optional[list[str]] = None
