"""Catálogo de patrones (solo lectura en v1, §6.3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from server.auth import require_user
from server.db import get_session
from server.models import Pattern

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("")
def list_patterns(_=Depends(require_user), session: Session = Depends(get_session)):
    patterns = session.exec(select(Pattern).order_by(Pattern.sort)).all()
    return [{"id": p.id, "label": p.label, "sort": p.sort} for p in patterns]
