"""Endpoints de autenticación (§6.2) con rate-limit básico de login en memoria."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from server.auth import (
    authenticate,
    hash_password,
    login_session,
    logout_session,
    require_user,
    verify_password,
)
from server.db import get_session
from server.models import User
from server.schemas import ChangePasswordIn, LoginIn

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate limit en memoria: máx. 5 intentos fallidos por IP en 60 s.
_LOGIN_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
_WINDOW_S = 60
_MAX_ATTEMPTS = 5


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    attempts = _LOGIN_ATTEMPTS[ip]
    while attempts and now - attempts[0] > _WINDOW_S:
        attempts.popleft()
    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera un minuto.",
        )


def _record_failure(ip: str) -> None:
    _LOGIN_ATTEMPTS[ip].append(time.time())


@router.post("/login")
def login(payload: LoginIn, request: Request, session: Session = Depends(get_session)):
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip)
    user = authenticate(session, payload.email.strip().lower(), payload.password)
    if not user:
        _record_failure(ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    login_session(request, user)
    return {"email": user.email}


@router.post("/logout")
def logout(request: Request):
    logout_session(request)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(require_user)):
    return {"email": user.email}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordIn,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if not verify_password(payload.current, user.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual no coincide")
    user.password_hash = hash_password(payload.next)
    session.add(user)
    session.commit()
    return {"ok": True}
