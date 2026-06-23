"""DTOs Pydantic de entrada/salida (validación de la API, §6)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from server.logic import VALID_BETTER, VALID_LEVELS, VALID_UNITS


# --- Auth ---
class LoginIn(BaseModel):
    email: str
    password: str


class ChangePasswordIn(BaseModel):
    current: str
    next: str = Field(min_length=6)


# --- Alumnos ---
class AthleteCreate(BaseModel):
    name: str = Field(min_length=1)


class AthletePatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    sort: Optional[int] = None
    archived: Optional[int] = None


class LevelsIn(BaseModel):
    """Mapa parcial patrón→nivel. Se validan claves/valores en el router."""
    empuje: Optional[str] = None
    traccion: Optional[str] = None
    pierna: Optional[str] = None
    carrera: Optional[str] = None
    core: Optional[str] = None

    def as_dict(self) -> dict[str, str]:
        out = {}
        for pattern_id, level in self.model_dump(exclude_none=True).items():
            if level not in VALID_LEVELS:
                raise ValueError(f"Nivel inválido para {pattern_id}: {level}")
            out[pattern_id] = level
        return out


# --- Rutinas ---
class DayPatch(BaseModel):
    name: Optional[str] = None
    focus: Optional[str] = None


class BlockCreate(BaseModel):
    title: str = Field(min_length=1)


class BlockPatch(BaseModel):
    title: Optional[str] = None
    sort: Optional[int] = None


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=1)
    pattern_id: str
    variant_a: str = ""
    variant_b: str = ""
    variant_c: str = ""
    media_a: str = ""
    media_b: str = ""
    media_c: str = ""


class ExercisePatch(BaseModel):
    name: Optional[str] = None
    pattern_id: Optional[str] = None
    variant_a: Optional[str] = None
    variant_b: Optional[str] = None
    variant_c: Optional[str] = None
    media_a: Optional[str] = None
    media_b: Optional[str] = None
    media_c: Optional[str] = None
    sort: Optional[int] = None


class ReorderIn(BaseModel):
    exercise_ids: list[int]


# --- Pruebas ---
class TestCreate(BaseModel):
    name: str = Field(min_length=1)
    pattern_id: str
    unit: str
    better: str

    def validate_catalog(self) -> None:
        if self.unit not in VALID_UNITS:
            raise ValueError(f"Unidad inválida: {self.unit}")
        if self.better not in VALID_BETTER:
            raise ValueError(f"Dirección inválida: {self.better}")


class TestPatch(BaseModel):
    name: Optional[str] = None
    pattern_id: Optional[str] = None
    unit: Optional[str] = None
    better: Optional[str] = None
    sort: Optional[int] = None
    archived: Optional[int] = None


# --- Sesiones de prueba ---
class MeasurementIn(BaseModel):
    athlete_id: int
    test_id: str
    raw_value: str = ""


class SessionCreate(BaseModel):
    date: int
    note: str = ""
    measurements: list[MeasurementIn] = []


class SessionPatch(BaseModel):
    date: Optional[int] = None
    note: Optional[str] = None
    measurements: Optional[list[MeasurementIn]] = None
