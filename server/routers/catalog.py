"""Catálogo de ejercicios: búsqueda de solo lectura (ver docs/CATALOGO-EJERCICIOS.md).

Fuente para autocompletar al crear ejercicios; no toca RoutineExercise. Se rellena con
`python -m server.import_catalog`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from server.auth import require_user
from server.db import get_session
from server.models import ExerciseCatalog
from server.services import normalize

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


def _to_dict(e: ExerciseCatalog) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "pattern_id": e.pattern_id,
        "media": e.media,
        "muscles": e.muscles,
        "equipment": e.equipment,
        "category": e.category,
    }


@router.get("")
def search_catalog(
    q: str = Query("", description="Texto de búsqueda (insensible a tildes)."),
    pattern: str | None = Query(None, description="Filtrar por patrón."),
    limit: int = Query(30, ge=1, le=50),
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    stmt = select(ExerciseCatalog)
    q_norm = normalize(q)
    if q_norm:
        stmt = stmt.where(ExerciseCatalog.name_norm.contains(q_norm))
    if pattern:
        stmt = stmt.where(ExerciseCatalog.pattern_id == pattern)
    stmt = stmt.order_by(ExerciseCatalog.name).limit(limit)
    return [_to_dict(e) for e in session.exec(stmt).all()]
