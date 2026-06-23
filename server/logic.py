"""Lógica de negocio: parseo de valores, deltas y resolución de variantes (§6.10)."""
from __future__ import annotations

from typing import Optional

VALID_LEVELS = {"A", "B", "C"}
VALID_UNITS = {"reps", "seg", "cm", "kg", "m", "mm:ss"}
VALID_BETTER = {"high", "low"}


def to_num(unit: str, raw: Optional[str]) -> Optional[float]:
    """Convierte un valor crudo a número comparable según la unidad.

    mm:ss → segundos. Devuelve None si está vacío o no es parseable.
    """
    if raw is None or raw.strip() == "":
        return None
    raw = raw.strip()
    try:
        if unit == "mm:ss":
            if ":" in raw:
                m, s = raw.split(":", 1)
                return int(m) * 60 + float(s.replace(",", "."))
            return float(raw.replace(",", "."))  # admite segundos sueltos
        return float(raw.replace(",", "."))
    except (ValueError, TypeError):
        return None


def delta(better: str, unit: str, cur_raw: str, prev_raw: str) -> Optional[dict]:
    """Diferencia cur-prev y si representa mejora según la dirección `better`."""
    cur, prev = to_num(unit, cur_raw), to_num(unit, prev_raw)
    if cur is None or prev is None:
        return None
    d = cur - prev
    if d == 0:
        return {"value": 0, "improved": None}
    improved = (d > 0) if better == "high" else (d < 0)
    return {"value": d, "improved": improved}


def resolve_variant(exercise, level: str) -> str:
    """Devuelve el texto de la variante correspondiente al nivel del alumno (§1.3).

    Fallback seguro a la variante A si el nivel es desconocido.
    """
    return {
        "A": exercise.variant_a,
        "B": exercise.variant_b,
        "C": exercise.variant_c,
    }.get(level, exercise.variant_a)


def format_value(unit: str, raw: str) -> str:
    """Formato legible para resúmenes (§6.10)."""
    raw = (raw or "").strip()
    if not raw:
        return raw
    if unit == "reps":
        return raw
    if unit == "mm:ss":
        return raw
    return f"{raw} {unit}"
