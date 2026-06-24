"""Catálogo global de niveles (iteración 3): CRUD + reordenar + borrado seguro."""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.auth import require_user
from server.db import get_session
from server.models import AthleteLevel, ExerciseVariant, Level
from server.schemas import LevelCreate, LevelPatch, LevelReorder
from server.services import default_level_id, levels_list

router = APIRouter(prefix="/api/levels", tags=["levels"])


def _slugify(name: str) -> str:
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")
    return slug or "nivel"


def _unique_slug(session: Session, base: str) -> str:
    slug, i = base, 2
    while session.get(Level, slug):
        slug = f"{base}-{i}"
        i += 1
    return slug


def _serialize(l: Level) -> dict:
    return {"id": l.id, "label": l.label, "color": l.color, "sort": l.sort}


@router.get("")
def list_levels(_=Depends(require_user), session: Session = Depends(get_session)):
    return [_serialize(l) for l in levels_list(session)]


@router.post("", status_code=201)
def create_level(
    payload: LevelCreate, _=Depends(require_user), session: Session = Depends(get_session)
):
    slug = _unique_slug(session, _slugify(payload.label))
    max_sort = session.exec(select(Level.sort).order_by(Level.sort.desc())).first()
    level = Level(id=slug, label=payload.label.strip(), color=payload.color, sort=(max_sort or 0) + 1)
    session.add(level)
    session.commit()
    return _serialize(level)


@router.patch("/{level_id}")
def patch_level(
    level_id: str,
    payload: LevelPatch,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    level = session.get(Level, level_id)
    if not level:
        raise HTTPException(status_code=404, detail="Nivel no encontrado")
    data = payload.model_dump(exclude_none=True)
    if "label" in data:
        level.label = data["label"].strip()
    if "color" in data:
        level.color = data["color"]
    if "sort" in data:
        level.sort = data["sort"]
    session.add(level)
    session.commit()
    return _serialize(level)


@router.put("/reorder")
def reorder_levels(
    payload: LevelReorder, _=Depends(require_user), session: Session = Depends(get_session)
):
    for new_sort, lid in enumerate(payload.level_ids, start=1):
        level = session.get(Level, lid)
        if level:
            level.sort = new_sort
            session.add(level)
    session.commit()
    return {"ok": True}


@router.delete("/{level_id}")
def delete_level(
    level_id: str, _=Depends(require_user), session: Session = Depends(get_session)
):
    """Borra un nivel. Reasigna los alumnos que lo usaban al primer nivel restante."""
    level = session.get(Level, level_id)
    if not level:
        raise HTTPException(status_code=404, detail="Nivel no encontrado")
    remaining = [l for l in levels_list(session) if l.id != level_id]
    if not remaining:
        raise HTTPException(status_code=400, detail="No puedes borrar el último nivel.")
    fallback = remaining[0].id

    # Reasigna niveles de alumnos que apuntaban a este.
    for al in session.exec(select(AthleteLevel).where(AthleteLevel.level == level_id)).all():
        al.level = fallback
        session.add(al)
    # Borra sus variantes de ejercicio.
    for v in session.exec(select(ExerciseVariant).where(ExerciseVariant.level_id == level_id)).all():
        session.delete(v)
    session.delete(level)
    session.commit()
    return {"ok": True, "reassigned_to": fallback}
