"""Import/Export de rutinas y pruebas en CSV (compatible con Excel).

Export: estado actual como CSV (sirve de plantilla, con BOM para acentos en Excel).
Import: REEMPLAZA todo (rutinas o pruebas) en una transacción.
- Rutinas: sin FK entrantes → borrado total + recreación.
- Pruebas: hay mediciones que referencian test_id → se hace upsert por id y las pruebas
  ausentes en el CSV se archivan (si tienen mediciones) o se borran (si no), preservando integridad.
"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlmodel import Session, select

from server.auth import require_user
from server.db import get_session
from server.logic import VALID_BETTER, VALID_UNITS
from server.models import Measurement, Pattern, RoutineBlock, RoutineDay, RoutineExercise, Test
from server.routers.tests import _slugify, _unique_slug

router = APIRouter(prefix="/api", tags=["csv"])

ROUTINE_COLUMNS = [
    "day_key", "day_name", "day_focus", "block_title", "block_sort",
    "exercise_name", "pattern_id", "variant_a", "variant_b", "variant_c",
    "media_a", "media_b", "media_c", "exercise_sort",
]
TEST_COLUMNS = ["id", "name", "pattern_id", "unit", "better", "sort"]


def _csv_response(columns: list[str], rows: list[list], filename: str) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows(rows)
    # BOM utf-8 para que Excel respete los acentos.
    content = "﻿" + buf.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _read_rows(file: UploadFile) -> list[dict]:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Archivo CSV vacío.")
    text = raw.decode("utf-8-sig", errors="replace")
    # Detecta delimitador (Excel en algunos locales usa ';').
    first_line = text.splitlines()[0] if text.splitlines() else ""
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]


# ---------------- Rutinas ----------------
@router.get("/export/routines.csv")
def export_routines(_=Depends(require_user), session: Session = Depends(get_session)):
    rows = []
    days = session.exec(select(RoutineDay).order_by(RoutineDay.sort)).all()
    for day in days:
        blocks = session.exec(
            select(RoutineBlock).where(RoutineBlock.day_key == day.day_key).order_by(RoutineBlock.sort)
        ).all()
        for block in blocks:
            items = session.exec(
                select(RoutineExercise)
                .where(RoutineExercise.block_id == block.id)
                .order_by(RoutineExercise.sort)
            ).all()
            for ex in items:
                rows.append([
                    day.day_key, day.name, day.focus, block.title, block.sort,
                    ex.name, ex.pattern_id, ex.variant_a, ex.variant_b, ex.variant_c,
                    ex.media_a, ex.media_b, ex.media_c, ex.sort,
                ])
    return _csv_response(ROUTINE_COLUMNS, rows, "rutinas.csv")


@router.post("/import/routines.csv")
async def import_routines(
    file: UploadFile = File(...),
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    rows = await _read_rows(file)
    if not rows:
        raise HTTPException(status_code=400, detail="El CSV no tiene filas.")
    missing = [c for c in ("day_key", "block_title", "exercise_name", "pattern_id") if c not in rows[0]]
    if missing:
        raise HTTPException(status_code=400, detail=f"Faltan columnas: {', '.join(missing)}")

    valid_patterns = {p.id for p in session.exec(select(Pattern)).all()}

    def to_int(v, default=0):
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return default

    days: dict[str, dict] = {}
    order: list[str] = []
    for i, r in enumerate(rows, start=2):  # fila 1 = cabecera
        dk = r.get("day_key", "")
        if not dk:
            continue
        pid = r.get("pattern_id", "")
        if pid not in valid_patterns:
            raise HTTPException(status_code=400, detail=f"Fila {i}: patrón inválido '{pid}'.")
        if dk not in days:
            days[dk] = {"name": r.get("day_name") or dk, "focus": r.get("day_focus", ""),
                        "sort": len(order) + 1, "blocks": {}}
            order.append(dk)
        blocks = days[dk]["blocks"]
        bt = r.get("block_title", "") or "Bloque"
        if bt not in blocks:
            blocks[bt] = {"sort": to_int(r.get("block_sort"), len(blocks) + 1), "items": []}
        blocks[bt]["items"].append({
            "name": r.get("exercise_name", "") or "Ejercicio",
            "pattern_id": pid,
            "variant_a": r.get("variant_a", ""), "variant_b": r.get("variant_b", ""),
            "variant_c": r.get("variant_c", ""),
            "media_a": r.get("media_a", ""), "media_b": r.get("media_b", ""),
            "media_c": r.get("media_c", ""),
            "sort": to_int(r.get("exercise_sort"), len(blocks[bt]["items"]) + 1),
        })

    # Reemplazo total (rutinas no tienen FK entrantes).
    for ex in session.exec(select(RoutineExercise)).all():
        session.delete(ex)
    for bl in session.exec(select(RoutineBlock)).all():
        session.delete(bl)
    for dy in session.exec(select(RoutineDay)).all():
        session.delete(dy)
    session.flush()

    for dk in order:
        d = days[dk]
        session.add(RoutineDay(day_key=dk, name=d["name"], focus=d["focus"], sort=d["sort"]))
        session.flush()
        for bt, b in sorted(d["blocks"].items(), key=lambda kv: kv[1]["sort"]):
            block = RoutineBlock(day_key=dk, title=bt, sort=b["sort"])
            session.add(block)
            session.flush()
            for esort, item in enumerate(sorted(b["items"], key=lambda x: x["sort"]), start=1):
                session.add(RoutineExercise(block_id=block.id, sort=esort, **{
                    k: item[k] for k in (
                        "name", "pattern_id", "variant_a", "variant_b", "variant_c",
                        "media_a", "media_b", "media_c",
                    )
                }))
    session.commit()
    return {"ok": True, "days": len(order)}


# ---------------- Pruebas ----------------
@router.get("/export/tests.csv")
def export_tests(_=Depends(require_user), session: Session = Depends(get_session)):
    rows = []
    for t in session.exec(select(Test).order_by(Test.sort, Test.id)).all():
        rows.append([t.id, t.name, t.pattern_id, t.unit, t.better, t.sort])
    return _csv_response(TEST_COLUMNS, rows, "pruebas.csv")


@router.post("/import/tests.csv")
async def import_tests(
    file: UploadFile = File(...),
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    rows = await _read_rows(file)
    if not rows:
        raise HTTPException(status_code=400, detail="El CSV no tiene filas.")
    if "name" not in rows[0] or "pattern_id" not in rows[0]:
        raise HTTPException(status_code=400, detail="Faltan columnas: name, pattern_id")

    valid_patterns = {p.id for p in session.exec(select(Pattern)).all()}

    def to_int(v, default=0):
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return default

    seen_ids: set[str] = set()
    for i, r in enumerate(rows, start=2):
        name = r.get("name", "")
        if not name:
            continue
        pid = r.get("pattern_id", "")
        unit = r.get("unit", "reps")
        better = r.get("better", "high")
        if pid not in valid_patterns:
            raise HTTPException(status_code=400, detail=f"Fila {i}: patrón inválido '{pid}'.")
        if unit not in VALID_UNITS:
            raise HTTPException(status_code=400, detail=f"Fila {i}: unidad inválida '{unit}'.")
        if better not in VALID_BETTER:
            raise HTTPException(status_code=400, detail=f"Fila {i}: dirección inválida '{better}'.")

        tid = r.get("id", "") or _unique_slug(session, _slugify(name))
        sort = to_int(r.get("sort"), i)
        existing = session.get(Test, tid)
        if existing:
            existing.name, existing.pattern_id = name, pid
            existing.unit, existing.better, existing.sort = unit, better, sort
            existing.archived = 0
            session.add(existing)
        else:
            session.add(Test(id=tid, name=name, pattern_id=pid, unit=unit, better=better, sort=sort))
        seen_ids.add(tid)

    # Pruebas ausentes en el CSV: archivar si tienen mediciones, borrar si no (preserva integridad).
    for t in session.exec(select(Test)).all():
        if t.id in seen_ids:
            continue
        has_meas = session.exec(select(Measurement).where(Measurement.test_id == t.id).limit(1)).first()
        if has_meas:
            t.archived = 1
            session.add(t)
        else:
            session.delete(t)
    session.commit()
    return {"ok": True, "tests": len(seen_ids)}
