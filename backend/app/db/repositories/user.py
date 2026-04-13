from typing import Optional
import uuid

from sqlalchemy.orm import Session

from app.auth.service import hash_password
from app.db.models import User


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, username: str, password: str, role: str = "admin") -> User:
    user = User(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


def delete_user(db: Session, user_id: str) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return False
    db.delete(user)
    db.commit()
    return True


def ensure_default_admin(db: Session, username: str, password: str):
    """Create default admin user if no users exist."""
    if db.query(User).count() == 0:
        create_user(db, username, password, role="admin")
