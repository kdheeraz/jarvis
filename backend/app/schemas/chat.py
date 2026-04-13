from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    message_id: str


class WSMessage(BaseModel):
    type: str  # message | stop | ping
    content: Optional[str] = None


class WSResponse(BaseModel):
    type: str  # chunk | tool_call | tool_result | done | error | pong
    content: Optional[str] = None
    name: Optional[str] = None
    args: Optional[dict] = None
    message_id: Optional[str] = None
    full_content: Optional[str] = None
    message: Optional[str] = None
