from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.middleware import require_admin
from app.db.engine import get_db
from app.db.repositories.user import create_user, delete_user, get_user_by_username, list_users
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserOut])
def get_users(db: Session = Depends(get_db)):
    return list_users(db)


@router.post("", response_model=UserOut, status_code=201)
def add_user(request: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_username(db, request.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    return create_user(db, request.username, request.password, request.role)


@router.delete("/{user_id}", status_code=204)
def remove_user(user_id: str, db: Session = Depends(get_db)):
    if not delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
