"""Lógica de negocio: parseo de valores, deltas y resolución de variantes (§6.10)."""
from __future__ import annotations

from typing import Optional

# Los niveles válidos ya no son fijos: se validan contra la tabla `levels` (iteración 3).
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


def resolve_variant(variants: dict, level_id: str) -> str:
    """Texto de la variante del nivel del alumno (§1.3), desde el dict {level_id: {text, media}}.

    Fallback seguro a cadena vacía si no hay variante para ese nivel.
    """
    entry = variants.get(level_id)
    return (entry or {}).get("text", "") if entry else ""


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
