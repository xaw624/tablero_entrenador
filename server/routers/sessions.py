"""Sesiones de prueba y mediciones (§6.7)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.auth import now_ms, require_user
from server.db import get_session
from server.models import Measurement, TestSession
from server.schemas import SessionCreate, SessionPatch

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _measurements_of(session: Session, session_id: int) -> list[dict]:
    rows = session.exec(
        select(Measurement).where(Measurement.session_id == session_id)
    ).all()
    return [
        {"athlete_id": m.athlete_id, "test_id": m.test_id, "raw_value": m.raw_value}
        for m in rows
    ]


def _dedup_nonempty(measurements) -> dict[tuple[int, str], str]:
    """Ignora raw_value vacío; si (athlete,test) se repite, el último gana."""
    out: dict[tuple[int, str], str] = {}
    for m in measurements:
        raw = (m.raw_value or "").strip()
        if raw == "":
            continue
        out[(m.athlete_id, m.test_id)] = raw
    return out


@router.get("")
def list_sessions(_=Depends(require_user), session: Session = Depends(get_session)):
    rows = session.exec(select(TestSession).order_by(TestSession.date)).all()
    return [
        {"id": s.id, "date": s.date, "note": s.note, "created_at": s.created_at} for s in rows
    ]


@router.get("/latest")
def latest_session(_=Depends(require_user), session: Session = Depends(get_session)):
    s = session.exec(
        select(TestSession).order_by(TestSession.date.desc(), TestSession.id.desc())
    ).first()
    if not s:
        return None
    return {
        "id": s.id,
        "date": s.date,
        "note": s.note,
        "measurements": _measurements_of(session, s.id),
    }


@router.get("/{session_id}")
def get_session_detail(
    session_id: int, _=Depends(require_user), session: Session = Depends(get_session)
):
    s = session.get(TestSession, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {
        "id": s.id,
        "date": s.date,
        "note": s.note,
        "measurements": _measurements_of(session, s.id),
    }


@router.post("", status_code=201)
def create_session(
    payload: SessionCreate, _=Depends(require_user), session: Session = Depends(get_session)
):
    ts = TestSession(date=payload.date, note=payload.note, created_at=now_ms())
    session.add(ts)
    session.commit()
    session.refresh(ts)
    for (athlete_id, test_id), raw in _dedup_nonempty(payload.measurements).items():
        session.add(
            Measurement(session_id=ts.id, athlete_id=athlete_id, test_id=test_id, raw_value=raw)
        )
    session.commit()
    return {
        "id": ts.id,
        "date": ts.date,
        "note": ts.note,
        "measurements": _measurements_of(session, ts.id),
    }


@router.patch("/{session_id}")
def patch_session(
    session_id: int,
    payload: SessionPatch,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    s = session.get(TestSession, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if payload.date is not None:
        s.date = payload.date
    if payload.note is not None:
        s.note = payload.note
    session.add(s)
    if payload.measurements is not None:
        # Reemplaza el set completo de la sesión.
        existing = session.exec(
            select(Measurement).where(Measurement.session_id == session_id)
        ).all()
        for m in existing:
            session.delete(m)
        for (athlete_id, test_id), raw in _dedup_nonempty(payload.measurements).items():
            session.add(
                Measurement(
                    session_id=session_id, athlete_id=athlete_id, test_id=test_id, raw_value=raw
                )
            )
    session.commit()
    return {
        "id": s.id,
        "date": s.date,
        "note": s.note,
        "measurements": _measurements_of(session, s.id),
    }


@router.delete("/{session_id}")
def delete_session(
    session_id: int, _=Depends(require_user), session: Session = Depends(get_session)
):
    s = session.get(TestSession, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    existing = session.exec(
        select(Measurement).where(Measurement.session_id == session_id)
    ).all()
    for m in existing:
        session.delete(m)
    session.delete(s)
    session.commit()
    return {"ok": True}
