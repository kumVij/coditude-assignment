from datetime import datetime, timedelta, timezone
from functools import lru_cache

import base64
import hashlib
import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import db_models

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@lru_cache
def get_fernet() -> Fernet:
    key = get_settings().pii_encryption_key
    if not key:
        if get_settings().auth_required:
            raise RuntimeError("PII_ENCRYPTION_KEY must be configured")
        key = base64.urlsafe_b64encode(hashlib.sha256(b"local-development-only").digest()).decode()
    return Fernet(key.encode())


def encrypt_pii(value: str | None) -> str | None:
    return get_fernet().encrypt(value.encode()).decode() if value else None


def decrypt_pii(value: str | None) -> str | None:
    return get_fernet().decrypt(value.encode()).decode() if value else None


def pii_hash(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY must be configured")
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": user_id, "exp": expires}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> db_models.User | None:
    settings = get_settings()
    if not token:
        if settings.auth_required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
    except (jwt.InvalidTokenError, RuntimeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.get(db_models.User, user_id)
    if not user or user.is_active != "true":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user