"""Gestión de alumnos y niveles por patrón (§6.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.auth import now_ms, require_user
from server.db import get_session
from server.models import Athlete, AthleteLevel, Level, Pattern
from server.schemas import AthleteCreate, AthletePatch, LevelsIn
from server.services import default_level_id, levels_map, pattern_ids

router = APIRouter(prefix="/api/athletes", tags=["athletes"])


def _serialize(session: Session, athlete: Athlete) -> dict:
    return {
        "id": athlete.id,
        "name": athlete.name,
        "sort": athlete.sort,
        "archived": athlete.archived,
        "levels": levels_map(session, athlete.id),
    }


@router.get("")
def list_athletes(
    include_archived: bool = False,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    query = select(Athlete)
    if not include_archived:
        query = query.where(Athlete.archived == 0)
    athletes = session.exec(query.order_by(Athlete.sort, Athlete.id)).all()
    return [_serialize(session, a) for a in athletes]


@router.post("", status_code=201)
def create_athlete(
    payload: AthleteCreate,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    max_sort = session.exec(select(Athlete.sort).order_by(Athlete.sort.desc())).first()
    athlete = Athlete(
        name=payload.name.strip(),
        sort=(max_sort or 0) + 1,
        created_at=now_ms(),
        archived=0,
    )
    session.add(athlete)
    session.commit()
    session.refresh(athlete)

    # Inicializa al nivel por defecto (el de menor sort) en todos los patrones.
    default = default_level_id(session)
    for pid in pattern_ids(session):
        session.add(AthleteLevel(athlete_id=athlete.id, pattern_id=pid, level=default))
    session.commit()
    return _serialize(session, athlete)


@router.patch("/{athlete_id}")
def patch_athlete(
    athlete_id: int,
    payload: AthletePatch,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    athlete = session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    data = payload.model_dump(exclude_none=True)
    if "name" in data:
        athlete.name = data["name"].strip()
    if "sort" in data:
        athlete.sort = data["sort"]
    if "archived" in data:
        athlete.archived = 1 if data["archived"] else 0
    session.add(athlete)
    session.commit()
    session.refresh(athlete)
    return _serialize(session, athlete)


@router.put("/{athlete_id}/levels")
def set_levels(
    athlete_id: int,
    payload: LevelsIn,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    athlete = session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    try:
        updates = payload.as_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    valid_patterns = set(pattern_ids(session))
    for pid, level in updates.items():
        if pid not in valid_patterns:
            raise HTTPException(status_code=400, detail=f"Patrón inválido: {pid}")
        if not session.get(Level, level):
            raise HTTPException(status_code=400, detail=f"Nivel inválido: {level}")
        row = session.get(AthleteLevel, (athlete_id, pid))
        if row:
            row.level = level
            session.add(row)
        else:
            session.add(AthleteLevel(athlete_id=athlete_id, pattern_id=pid, level=level))
    session.commit()
    return _serialize(session, athlete)


@router.delete("/{athlete_id}")
def delete_athlete(
    athlete_id: int,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    """Soft delete: archived=1 para preservar historial de mediciones."""
    athlete = session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    athlete.archived = 1
    session.add(athlete)
    session.commit()
    return {"ok": True}
