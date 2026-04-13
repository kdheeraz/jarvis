from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


def _to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=_to_camel, populate_by_name=True)

    id: str
    role: str
    content: str
    tool_name: Optional[str] = None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=_to_camel, populate_by_name=True)

    id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []
