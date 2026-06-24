"""Rutinas: lectura anidada, resolución por alumno, edición y CRUD de días (§6.5 + it.3)."""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.auth import require_user
from server.db import get_session
from server.models import (
    Athlete,
    ExerciseVariant,
    Level,
    Pattern,
    RoutineBlock,
    RoutineDay,
    RoutineExercise,
)
from server.schemas import (
    BlockCreate,
    BlockPatch,
    DayCreate,
    DayPatch,
    DayReorder,
    ExerciseCreate,
    ExercisePatch,
    ReorderIn,
    VariantIn,
)
from server.services import level_ids, levels_map

router = APIRouter(prefix="/api/routines", tags=["routines"])


def _variants_map(session: Session, exercise_id: int) -> dict[str, dict]:
    rows = session.exec(
        select(ExerciseVariant).where(ExerciseVariant.exercise_id == exercise_id)
    ).all()
    return {v.level_id: {"text": v.text, "media": v.media} for v in rows}


def _exercise_dict(session: Session, ex: RoutineExercise) -> dict:
    return {
        "id": ex.id,
        "name": ex.name,
        "pattern_id": ex.pattern_id,
        "sort": ex.sort,
        "variants": _variants_map(session, ex.id),
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
                "items": [_exercise_dict(session, i) for i in items],
            }
        )
    return {
        "day_key": day.day_key,
        "name": day.name,
        "focus": day.focus,
        "sort": day.sort,
        "weekday": day.weekday,
        "blocks": out_blocks,
    }


def _get_day_or_404(session: Session, day_key: str) -> RoutineDay:
    day = session.get(RoutineDay, day_key)
    if not day:
        raise HTTPException(status_code=404, detail="Día no encontrado")
    return day


def _slugify(name: str) -> str:
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")
    return slug or "dia"


def _delete_exercise_full(session: Session, ex: RoutineExercise) -> None:
    for v in session.exec(
        select(ExerciseVariant).where(ExerciseVariant.exercise_id == ex.id)
    ).all():
        session.delete(v)
    session.delete(ex)


# --- Lectura ---
@router.get("")
def all_routines(_=Depends(require_user), session: Session = Depends(get_session)):
    days = session.exec(select(RoutineDay).order_by(RoutineDay.sort)).all()
    return {d.day_key: _serialize_day(session, d) for d in days}


# --- CRUD de días (declarado antes de /{day_key}) ---
@router.post("/days", status_code=201)
def create_day(
    payload: DayCreate, _=Depends(require_user), session: Session = Depends(get_session)
):
    base = (payload.day_key or _slugify(payload.name)).strip()
    key, i = base, 2
    while session.get(RoutineDay, key):
        key = f"{base}-{i}"
        i += 1
    max_sort = session.exec(select(RoutineDay.sort).order_by(RoutineDay.sort.desc())).first()
    day = RoutineDay(
        day_key=key, name=payload.name.strip(), focus=payload.focus,
        sort=(max_sort or 0) + 1, weekday=payload.weekday,
    )
    session.add(day)
    session.commit()
    return _serialize_day(session, day)


@router.put("/days/reorder")
def reorder_days(
    payload: DayReorder, _=Depends(require_user), session: Session = Depends(get_session)
):
    for new_sort, dk in enumerate(payload.day_keys, start=1):
        day = session.get(RoutineDay, dk)
        if day:
            day.sort = new_sort
            session.add(day)
    session.commit()
    return {"ok": True}


@router.delete("/days/{day_key}")
def delete_day(
    day_key: str, _=Depends(require_user), session: Session = Depends(get_session)
):
    day = _get_day_or_404(session, day_key)
    blocks = session.exec(select(RoutineBlock).where(RoutineBlock.day_key == day_key)).all()
    for block in blocks:
        for ex in session.exec(
            select(RoutineExercise).where(RoutineExercise.block_id == block.id)
        ).all():
            _delete_exercise_full(session, ex)
        session.delete(block)
    session.delete(day)
    session.commit()
    return {"ok": True}


# --- Edición de bloques/ejercicios ---
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
    for ex in session.exec(
        select(RoutineExercise).where(RoutineExercise.block_id == block_id)
    ).all():
        _delete_exercise_full(session, ex)
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
        block_id=block_id, name=payload.name.strip(),
        pattern_id=payload.pattern_id, sort=(max_sort or 0) + 1,
    )
    session.add(ex)
    session.commit()
    session.refresh(ex)
    # Crea variantes vacías para cada nivel existente.
    for lid in level_ids(session):
        session.add(ExerciseVariant(exercise_id=ex.id, level_id=lid, text="", media=""))
    session.commit()
    return _exercise_dict(session, ex)


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
    for key in ("name", "pattern_id", "sort"):
        if key in data:
            setattr(ex, key, data[key])
    session.add(ex)
    session.commit()
    session.refresh(ex)
    return _exercise_dict(session, ex)


@router.put("/exercises/{exercise_id}/variants/{level_id}")
def set_variant(
    exercise_id: int,
    level_id: str,
    payload: VariantIn,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    if not session.get(RoutineExercise, exercise_id):
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    if not session.get(Level, level_id):
        raise HTTPException(status_code=400, detail=f"Nivel inválido: {level_id}")
    row = session.get(ExerciseVariant, (exercise_id, level_id))
    if not row:
        row = ExerciseVariant(exercise_id=exercise_id, level_id=level_id, text="", media="")
    if payload.text is not None:
        row.text = payload.text
    if payload.media is not None:
        row.media = payload.media
    session.add(row)
    session.commit()
    return {"exercise_id": exercise_id, "level_id": level_id, "text": row.text, "media": row.media}


@router.delete("/exercises/{exercise_id}")
def delete_exercise(
    exercise_id: int,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    ex = session.get(RoutineExercise, exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    _delete_exercise_full(session, ex)
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


# --- Lectura por día / por alumno (rutas con {day_key}, al final) ---
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
    if "weekday" in data:
        day.weekday = data["weekday"]
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
    """Resuelve texto+medio por alumno (algoritmo §1.3) para la vista 'Por alumno'."""
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
            level = levels.get(ex.pattern_id)
            variants = _variants_map(session, ex.id)
            entry = variants.get(level, {}) if level else {}
            out_items.append(
                {
                    "id": ex.id,
                    "name": ex.name,
                    "pattern_id": ex.pattern_id,
                    "level": level,
                    "text": entry.get("text", ""),
                    "media": entry.get("media", ""),
                }
            )
        out_blocks.append({"title": block.title, "items": out_items})
    return {"day_key": day.day_key, "name": day.name, "focus": day.focus, "blocks": out_blocks}
