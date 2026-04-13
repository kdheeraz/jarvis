from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.db.repositories.conversation import create_conversation, get_conversation
from app.voice.stream import bind_voice_conversation, get_voice_stream

router = APIRouter(prefix="/api/voice", tags=["voice"])


class VoiceBindRequest(BaseModel):
    webrtc_id: str
    conversation_id: str | None = None


class VoiceBindResponse(BaseModel):
    conversation_id: str
    bound: bool


@router.post("/bind", response_model=VoiceBindResponse)
def bind(body: VoiceBindRequest, db: Session = Depends(get_db)):
    """Attach (or create) a conversation for an active voice WebRTC session.

    Called by the frontend immediately after the WebRTC offer is accepted.
    If no conversation_id is supplied (or it's "new"), a fresh conversation
    row is created so it shows up in the sidebar like any other chat.
    """
    if get_voice_stream() is None:
        raise HTTPException(status_code=503, detail="Voice stream not available")

    conversation_id = body.conversation_id
    if not conversation_id or conversation_id == "new":
        conv = create_conversation(db, title="Voice chat")
        conversation_id = conv.id
    else:
        if get_conversation(db, conversation_id) is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

    bound = bind_voice_conversation(body.webrtc_id, conversation_id)
    return VoiceBindResponse(conversation_id=conversation_id, bound=bound)
