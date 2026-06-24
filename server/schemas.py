"""DTOs Pydantic de entrada/salida (validación de la API, §6)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from server.logic import VALID_BETTER, VALID_UNITS


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
    """Mapa parcial patrón→level_id. Los valores se validan contra `levels` en el router."""
    empuje: Optional[str] = None
    traccion: Optional[str] = None
    pierna: Optional[str] = None
    carrera: Optional[str] = None
    core: Optional[str] = None

    def as_dict(self) -> dict[str, str]:
        return dict(self.model_dump(exclude_none=True))


# --- Niveles (catálogo global) ---
class LevelCreate(BaseModel):
    label: str = Field(min_length=1)
    color: str = "#888888"


class LevelPatch(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1)
    color: Optional[str] = None
    sort: Optional[int] = None


class LevelReorder(BaseModel):
    level_ids: list[str]


# --- Rutinas ---
class DayPatch(BaseModel):
    name: Optional[str] = None
    focus: Optional[str] = None
    weekday: Optional[int] = Field(default=None, ge=0, le=6)


class DayCreate(BaseModel):
    name: str = Field(min_length=1)
    focus: str = ""
    weekday: Optional[int] = Field(default=None, ge=0, le=6)
    day_key: Optional[str] = None  # si falta se genera del nombre


class DayReorder(BaseModel):
    day_keys: list[str]


class VariantIn(BaseModel):
    text: Optional[str] = None
    media: Optional[str] = None


class BlockCreate(BaseModel):
    title: str = Field(min_length=1)


class BlockPatch(BaseModel):
    title: Optional[str] = None
    sort: Optional[int] = None


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=1)
    pattern_id: str


class ExercisePatch(BaseModel):
    name: Optional[str] = None
    pattern_id: Optional[str] = None
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
