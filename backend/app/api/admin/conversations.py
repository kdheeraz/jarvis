from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.middleware import require_admin
from app.db.engine import get_db
from app.db.repositories.conversation import delete_conversation, get_conversation, list_conversations
from app.schemas.conversation import ConversationDetailOut, ConversationOut

router = APIRouter(prefix="/api/admin/conversations", tags=["admin-conversations"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[ConversationOut])
def get_all_conversations(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    return list_conversations(db, limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation_detail(conversation_id: str, db: Session = Depends(get_db)):
    conv = get_conversation(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}", status_code=204)
def remove_conversation(conversation_id: str, db: Session = Depends(get_db)):
    if not delete_conversation(db, conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
