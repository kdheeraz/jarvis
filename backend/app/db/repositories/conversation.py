from typing import Optional
import uuid

from sqlalchemy.orm import Session

from app.db.models import Conversation, Message


def create_conversation(db: Session, title: Optional[str] = None, session_id: Optional[str] = None) -> Conversation:
    conv = Conversation(id=str(uuid.uuid4()), title=title, session_id=session_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def list_conversations(db: Session, limit: int = 50, offset: int = 0) -> list[Conversation]:
    return (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def delete_conversation(db: Session, conversation_id: str) -> bool:
    conv = get_conversation(db, conversation_id)
    if conv is None:
        return False
    db.delete(conv)
    db.commit()
    return True


def add_message(db: Session, conversation_id: str, role: str, content: str, **kwargs) -> Message:
    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_name=kwargs.get("tool_name"),
        tool_call_id=kwargs.get("tool_call_id"),
        metadata_json=kwargs.get("metadata_json"),
    )
    db.add(msg)
    # Update conversation timestamp
    conv = get_conversation(db, conversation_id)
    if conv and not conv.title and role == "user":
        conv.title = content[:100]
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(db: Session, conversation_id: str) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
