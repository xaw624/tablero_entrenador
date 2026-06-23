"""Autenticación: hashing bcrypt, sesión por cookie y dependency require_user."""
from __future__ import annotations

import time

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from server.db import get_session
from server.models import User


def _to_bytes(password: str) -> bytes:
    # bcrypt admite máximo 72 bytes; truncamos de forma estable (práctica estándar).
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def now_ms() -> int:
    return int(time.time() * 1000)


def login_session(request: Request, user: User) -> None:
    request.session["uid"] = user.id


def logout_session(request: Request) -> None:
    request.session.clear()


def require_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    """Dependency: exige sesión válida. 401 si no hay usuario."""
    uid = request.session.get("uid")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    user = session.get(User, uid)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return user


def authenticate(session: Session, email: str, password: str) -> User | None:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user
