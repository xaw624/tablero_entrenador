"""Helpers de acceso a datos compartidos entre routers."""
from __future__ import annotations

from sqlmodel import Session, select

from server.models import AthleteLevel, Pattern

DEFAULT_LEVEL = "A"


def pattern_ids(session: Session) -> list[str]:
    return [p.id for p in session.exec(select(Pattern).order_by(Pattern.sort)).all()]


def levels_map(session: Session, athlete_id: int) -> dict[str, str]:
    """Devuelve {pattern_id: level} para un alumno, con fallback 'A' en patrones faltantes."""
    rows = session.exec(
        select(AthleteLevel).where(AthleteLevel.athlete_id == athlete_id)
    ).all()
    existing = {r.pattern_id: r.level for r in rows}
    return {pid: existing.get(pid, DEFAULT_LEVEL) for pid in pattern_ids(session)}
