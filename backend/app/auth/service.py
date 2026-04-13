from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from loguru import logger

from app.config import get_config


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(username: str, role: str) -> str:
    config = get_config()
    expires = datetime.now(timezone.utc) + timedelta(minutes=config.auth.jwt_expiry_minutes)
    payload = {
        "sub": username,
        "role": role,
        "exp": expires,
    }
    return jwt.encode(payload, config.auth.jwt_secret_key, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    config = get_config()
    try:
        return jwt.decode(token, config.auth.jwt_secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
