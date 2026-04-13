from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.db.repositories.conversation import (
    delete_conversation,
    get_conversation,
    list_conversations,
)
from app.schemas.conversation import ConversationDetailOut, ConversationOut, MessageOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut], response_model_by_alias=True)
def get_conversations(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    return list_conversations(db, limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationDetailOut, response_model_by_alias=True)
def get_conversation_detail(conversation_id: str, db: Session = Depends(get_db)):
    conv = get_conversation(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}", status_code=204)
def remove_conversation(conversation_id: str, db: Session = Depends(get_db)):
    if not delete_conversation(db, conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
