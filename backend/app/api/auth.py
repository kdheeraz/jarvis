from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.middleware import require_admin
from app.auth.service import create_access_token, verify_password
from app.db.engine import get_db
from app.db.repositories.user import get_user_by_username
from app.schemas.user import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_username(db, request.username)
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(user.username, user.role)
    return LoginResponse(access_token=token)


@router.get("/me")
def get_current_user(payload: dict = Depends(require_admin)):
    return {"username": payload["sub"], "role": payload["role"]}
