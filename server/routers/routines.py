"""Rutinas: lectura anidada, resolución por alumno y edición (§6.5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.auth import require_user
from server.db import get_session
from server.logic import resolve_variant
from server.models import (
    Athlete,
    Pattern,
    RoutineBlock,
    RoutineDay,
    RoutineExercise,
)
from server.schemas import (
    BlockCreate,
    BlockPatch,
    DayPatch,
    ExerciseCreate,
    ExercisePatch,
    ReorderIn,
)
from server.services import levels_map

router = APIRouter(prefix="/api/routines", tags=["routines"])


def _exercise_dict(ex: RoutineExercise) -> dict:
    return {
        "id": ex.id,
        "name": ex.name,
        "pattern_id": ex.pattern_id,
        "variant_a": ex.variant_a,
        "variant_b": ex.variant_b,
        "variant_c": ex.variant_c,
        "media_a": ex.media_a,
        "media_b": ex.media_b,
        "media_c": ex.media_c,
        "sort": ex.sort,
    }


def _serialize_day(session: Session, day: RoutineDay) -> dict:
    blocks = session.exec(
        select(RoutineBlock).where(RoutineBlock.day_key == day.day_key).order_by(RoutineBlock.sort)
    ).all()
    out_blocks = []
    for block in blocks:
        items = session.exec(
            select(RoutineExercise)
            .where(RoutineExercise.block_id == block.id)
            .order_by(RoutineExercise.sort)
        ).all()
        out_blocks.append(
            {
                "id": block.id,
                "title": block.title,
                "sort": block.sort,
                "items": [_exercise_dict(i) for i in items],
            }
        )
    return {
        "day_key": day.day_key,
        "name": day.name,
        "focus": day.focus,
        "sort": day.sort,
        "blocks": out_blocks,
    }


def _get_day_or_404(session: Session, day_key: str) -> RoutineDay:
    day = session.get(RoutineDay, day_key)
    if not day:
        raise HTTPException(status_code=404, detail="Día no encontrado")
    return day


# --- Lectura ---
@router.get("")
def all_routines(_=Depends(require_user), session: Session = Depends(get_session)):
    days = session.exec(select(RoutineDay).order_by(RoutineDay.sort)).all()
    return {d.day_key: _serialize_day(session, d) for d in days}


# --- Edición de bloques/ejercicios (rutas declaradas antes de /{day_key}) ---
@router.post("/{day_key}/blocks", status_code=201)
def create_block(
    day_key: str,
    payload: BlockCreate,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    _get_day_or_404(session, day_key)
    max_sort = session.exec(
        select(RoutineBlock.sort)
        .where(RoutineBlock.day_key == day_key)
        .order_by(RoutineBlock.sort.desc())
    ).first()
    block = RoutineBlock(day_key=day_key, title=payload.title.strip(), sort=(max_sort or 0) + 1)
    session.add(block)
    session.commit()
    session.refresh(block)
    return {"id": block.id, "title": block.title, "sort": block.sort, "items": []}


@router.patch("/blocks/{block_id}")
def patch_block(
    block_id: int,
    payload: BlockPatch,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    block = session.get(RoutineBlock, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Bloque no encontrado")
    data = payload.model_dump(exclude_none=True)
    if "title" in data:
        block.title = data["title"].strip()
    if "sort" in data:
        block.sort = data["sort"]
    session.add(block)
    session.commit()
    return {"id": block.id, "title": block.title, "sort": block.sort}


@router.delete("/blocks/{block_id}")
def delete_block(
    block_id: int,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    block = session.get(RoutineBlock, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Bloque no encontrado")
    # Cascade manual: borrar ejercicios del bloque.
    exercises = session.exec(
        select(RoutineExercise).where(RoutineExercise.block_id == block_id)
    ).all()
    for ex in exercises:
        session.delete(ex)
    session.delete(block)
    session.commit()
    return {"ok": True}


@router.post("/blocks/{block_id}/exercises", status_code=201)
def create_exercise(
    block_id: int,
    payload: ExerciseCreate,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    if not session.get(RoutineBlock, block_id):
        raise HTTPException(status_code=404, detail="Bloque no encontrado")
    if not session.get(Pattern, payload.pattern_id):
        raise HTTPException(status_code=400, detail=f"Patrón inválido: {payload.pattern_id}")
    max_sort = session.exec(
        select(RoutineExercise.sort)
        .where(RoutineExercise.block_id == block_id)
        .order_by(RoutineExercise.sort.desc())
    ).first()
    ex = RoutineExercise(
        block_id=block_id,
        name=payload.name.strip(),
        pattern_id=payload.pattern_id,
        variant_a=payload.variant_a,
        variant_b=payload.variant_b,
        variant_c=payload.variant_c,
        media_a=payload.media_a,
        media_b=payload.media_b,
        media_c=payload.media_c,
        sort=(max_sort or 0) + 1,
    )
    session.add(ex)
    session.commit()
    session.refresh(ex)
    return _exercise_dict(ex)


@router.patch("/exercises/{exercise_id}")
def patch_exercise(
    exercise_id: int,
    payload: ExercisePatch,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    ex = session.get(RoutineExercise, exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    data = payload.model_dump(exclude_none=True)
    if "pattern_id" in data and not session.get(Pattern, data["pattern_id"]):
        raise HTTPException(status_code=400, detail=f"Patrón inválido: {data['pattern_id']}")
    for key in (
        "name", "pattern_id", "variant_a", "variant_b", "variant_c",
        "media_a", "media_b", "media_c", "sort",
    ):
        if key in data:
            setattr(ex, key, data[key])
    session.add(ex)
    session.commit()
    session.refresh(ex)
    return _exercise_dict(ex)


@router.delete("/exercises/{exercise_id}")
def delete_exercise(
    exercise_id: int,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    ex = session.get(RoutineExercise, exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    session.delete(ex)
    session.commit()
    return {"ok": True}


@router.put("/blocks/{block_id}/reorder")
def reorder_exercises(
    block_id: int,
    payload: ReorderIn,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    if not session.get(RoutineBlock, block_id):
        raise HTTPException(status_code=404, detail="Bloque no encontrado")
    for new_sort, ex_id in enumerate(payload.exercise_ids):
        ex = session.get(RoutineExercise, ex_id)
        if ex and ex.block_id == block_id:
            ex.sort = new_sort
            session.add(ex)
    session.commit()
    return {"ok": True}


# --- Lectura por día / por alumno (rutas con {day_key}, declaradas al final) ---
@router.get("/{day_key}")
def one_day(day_key: str, _=Depends(require_user), session: Session = Depends(get_session)):
    day = _get_day_or_404(session, day_key)
    return _serialize_day(session, day)


@router.patch("/{day_key}")
def patch_day(
    day_key: str,
    payload: DayPatch,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    day = _get_day_or_404(session, day_key)
    data = payload.model_dump(exclude_none=True)
    if "name" in data:
        day.name = data["name"]
    if "focus" in data:
        day.focus = data["focus"]
    session.add(day)
    session.commit()
    return _serialize_day(session, day)


@router.get("/{day_key}/for-athlete/{athlete_id}")
def day_for_athlete(
    day_key: str,
    athlete_id: int,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    """Resuelve la variante por alumno (algoritmo §1.3) para la vista 'Por alumno'."""
    day = _get_day_or_404(session, day_key)
    athlete = session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    levels = levels_map(session, athlete_id)

    blocks = session.exec(
        select(RoutineBlock).where(RoutineBlock.day_key == day_key).order_by(RoutineBlock.sort)
    ).all()
    out_blocks = []
    for block in blocks:
        items = session.exec(
            select(RoutineExercise)
            .where(RoutineExercise.block_id == block.id)
            .order_by(RoutineExercise.sort)
        ).all()
        out_items = []
        for ex in items:
            level = levels.get(ex.pattern_id, "A")
            media = {"A": ex.media_a, "B": ex.media_b, "C": ex.media_c}.get(level, ex.media_a)
            out_items.append(
                {
                    "id": ex.id,
                    "name": ex.name,
                    "pattern_id": ex.pattern_id,
                    "level": level,
                    "text": resolve_variant(ex, level),
                    "media": media,
                }
            )
        out_blocks.append({"title": block.title, "items": out_items})
    return {"day_key": day.day_key, "name": day.name, "focus": day.focus, "blocks": out_blocks}
