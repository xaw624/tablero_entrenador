"""Helpers de acceso a datos compartidos entre routers."""
from __future__ import annotations

from sqlmodel import Session, select

from server.models import AthleteLevel, Level, Pattern


def pattern_ids(session: Session) -> list[str]:
    return [p.id for p in session.exec(select(Pattern).order_by(Pattern.sort)).all()]


def levels_list(session: Session) -> list[Level]:
    return session.exec(select(Level).order_by(Level.sort, Level.id)).all()


def level_ids(session: Session) -> list[str]:
    return [l.id for l in levels_list(session)]


def default_level_id(session: Session) -> str:
    """Nivel por defecto = el de menor sort. 'A' como último recurso."""
    first = session.exec(select(Level).order_by(Level.sort, Level.id)).first()
    return first.id if first else "A"


def levels_map(session: Session, athlete_id: int) -> dict[str, str]:
    """Devuelve {pattern_id: level_id} para un alumno; fallback al nivel por defecto."""
    rows = session.exec(
        select(AthleteLevel).where(AthleteLevel.athlete_id == athlete_id)
    ).all()
    existing = {r.pattern_id: r.level for r in rows}
    fallback = default_level_id(session)
    return {pid: existing.get(pid, fallback) for pid in pattern_ids(session)}
