"""Series temporales de progreso por alumno + prueba (§6.8)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.auth import require_user
from server.db import get_session
from server.logic import to_num
from server.models import Measurement, Test, TestSession

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("")
def progress(
    athlete_id: int,
    test_id: str,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Prueba no encontrada")

    rows = session.exec(
        select(TestSession.date, Measurement.raw_value)
        .join(Measurement, Measurement.session_id == TestSession.id)
        .where(Measurement.athlete_id == athlete_id)
        .where(Measurement.test_id == test_id)
        .order_by(TestSession.date)
    ).all()

    points = []
    for date, raw in rows:
        num = to_num(test.unit, raw)
        if num is None:
            continue
        points.append({"date": date, "raw": raw, "num": num})

    return {
        "test": {"id": test.id, "name": test.name, "unit": test.unit, "better": test.better},
        "points": points,
    }
