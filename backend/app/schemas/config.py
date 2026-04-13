from typing import Optional

from pydantic import BaseModel


class ConfigUpdateRequest(BaseModel):
    """Partial config update — only include fields to change."""
    llm: Optional[dict] = None
    rag: Optional[dict] = None
    voice: Optional[dict] = None
    tools: Optional[dict] = None
    auth: Optional[dict] = None
    app: Optional[dict] = None
