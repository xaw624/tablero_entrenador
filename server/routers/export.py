"""Exportación / compartir y backup completo (§6.9, §6.10)."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from sqlmodel import Session, select

from server.auth import require_user
from server.db import get_session
from server.logic import format_value
from server.models import (
    Athlete,
    AthleteLevel,
    ExerciseVariant,
    Level,
    Measurement,
    Pattern,
    RoutineBlock,
    RoutineDay,
    RoutineExercise,
    Test,
    TestSession,
)

router = APIRouter(prefix="/api", tags=["export"])

_MESES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]


def _fmt_date(epoch_ms: int) -> str:
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    return f"{dt.day:02d} {_MESES[dt.month - 1]} {dt.year}"


def _session_or_404(session: Session, session_id: int) -> TestSession:
    s = session.get(TestSession, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return s


def _ordered_measurements(session: Session, session_id: int):
    """Devuelve (athlete, test, raw) ordenado por sort de alumno y de prueba."""
    rows = session.exec(
        select(Measurement).where(Measurement.session_id == session_id)
    ).all()
    by_key = {(m.athlete_id, m.test_id): m.raw_value for m in rows}
    athletes = session.exec(select(Athlete).order_by(Athlete.sort, Athlete.id)).all()
    tests = session.exec(select(Test).order_by(Test.sort, Test.id)).all()
    return athletes, tests, by_key


@router.get("/export/session/{session_id}.txt", response_class=PlainTextResponse)
def export_txt(
    session_id: int, _=Depends(require_user), session: Session = Depends(get_session)
):
    s = _session_or_404(session, session_id)
    athletes, tests, by_key = _ordered_measurements(session, session_id)
    lines = [f"MÉTODO FUNCIONAL — Resultados {_fmt_date(s.date)}", ""]
    for a in athletes:
        rows = [(t, by_key[(a.id, t.id)]) for t in tests if (a.id, t.id) in by_key]
        if not rows:
            continue
        lines.append(a.name)
        for t, raw in rows:
            lines.append(f"  · {t.name}: {format_value(t.unit, raw)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


@router.get("/export/session/{session_id}.csv")
def export_csv(
    session_id: int, _=Depends(require_user), session: Session = Depends(get_session)
):
    _session_or_404(session, session_id)
    athletes, tests, by_key = _ordered_measurements(session, session_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["alumno", "prueba", "unidad", "valor"])
    for a in athletes:
        for t in tests:
            if (a.id, t.id) in by_key:
                writer.writerow([a.name, t.name, t.unit, by_key[(a.id, t.id)]])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="sesion-{session_id}.csv"'},
    )


@router.get("/export/backup.json")
def export_backup(_=Depends(require_user), session: Session = Depends(get_session)):
    def dump(model):
        return [r.model_dump() for r in session.exec(select(model)).all()]

    return {
        "version": 2,
        "patterns": dump(Pattern),
        "levels": dump(Level),
        "athletes": dump(Athlete),
        "athlete_levels": dump(AthleteLevel),
        "routine_days": dump(RoutineDay),
        "routine_blocks": dump(RoutineBlock),
        "routine_exercises": dump(RoutineExercise),
        "exercise_variants": dump(ExerciseVariant),
        "tests": dump(Test),
        "test_sessions": dump(TestSession),
        "measurements": dump(Measurement),
    }


@router.post("/import/backup.json")
async def import_backup(
    request: Request, _=Depends(require_user), session: Session = Depends(get_session)
):
    """Restaura un volcado completo. Reemplaza todo salvo usuarios. Usar con confirmación en UI."""
    data = await request.json()
    if not isinstance(data, dict) or "patterns" not in data:
        raise HTTPException(status_code=400, detail="Backup inválido")

    order = [
        ("measurements", Measurement),
        ("test_sessions", TestSession),
        ("exercise_variants", ExerciseVariant),
        ("routine_exercises", RoutineExercise),
        ("routine_blocks", RoutineBlock),
        ("routine_days", RoutineDay),
        ("athlete_levels", AthleteLevel),
        ("athletes", Athlete),
        ("levels", Level),
        ("tests", Test),
        ("patterns", Pattern),
    ]
    # Borrar en orden inverso de dependencias.
    for _key, model in order:
        for row in session.exec(select(model)).all():
            session.delete(row)
    session.commit()
    # Insertar en orden de dependencias (reverso de la lista de borrado).
    for key, model in reversed(order):
        for item in data.get(key, []):
            session.add(model(**item))
    session.commit()
    return {"ok": True}
