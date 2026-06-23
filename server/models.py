"""Modelos SQLModel (tablas). Esquema relacional descrito en §5 de la especificación.

El nivel por patrón es relacional (tabla athlete_levels), no JSON, para integridad
referencial y para resolver variantes con joins limpios. Timestamps en epoch ms (INTEGER).
"""
from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: int


class Pattern(SQLModel, table=True):
    __tablename__ = "patterns"
    id: str = Field(primary_key=True)
    label: str
    sort: int


class Athlete(SQLModel, table=True):
    __tablename__ = "athletes"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sort: int = 0
    created_at: int
    archived: int = 0


class AthleteLevel(SQLModel, table=True):
    __tablename__ = "athlete_levels"
    athlete_id: int = Field(foreign_key="athletes.id", primary_key=True)
    pattern_id: str = Field(foreign_key="patterns.id", primary_key=True)
    level: str  # 'A' | 'B' | 'C'


class RoutineDay(SQLModel, table=True):
    __tablename__ = "routine_days"
    day_key: str = Field(primary_key=True)
    name: str
    focus: str
    sort: int


class RoutineBlock(SQLModel, table=True):
    __tablename__ = "routine_blocks"
    id: Optional[int] = Field(default=None, primary_key=True)
    day_key: str = Field(foreign_key="routine_days.day_key")
    title: str
    sort: int


class RoutineExercise(SQLModel, table=True):
    __tablename__ = "routine_exercises"
    id: Optional[int] = Field(default=None, primary_key=True)
    block_id: int = Field(foreign_key="routine_blocks.id")
    name: str
    pattern_id: str = Field(foreign_key="patterns.id")
    variant_a: str = ""
    variant_b: str = ""
    variant_c: str = ""
    # Medio por variante: ruta de archivo subido (/media/<x>) o URL de video externa.
    media_a: str = ""
    media_b: str = ""
    media_c: str = ""
    sort: int


class Test(SQLModel, table=True):
    __tablename__ = "tests"
    id: str = Field(primary_key=True)
    name: str
    pattern_id: str = Field(foreign_key="patterns.id")
    unit: str  # 'reps','seg','cm','kg','m','mm:ss'
    better: str  # 'high' | 'low'
    sort: int
    archived: int = 0


class TestSession(SQLModel, table=True):
    __tablename__ = "test_sessions"
    id: Optional[int] = Field(default=None, primary_key=True)
    date: int  # epoch ms (fecha elegida por el usuario)
    note: str = ""
    created_at: int


class Measurement(SQLModel, table=True):
    __tablename__ = "measurements"
    session_id: int = Field(foreign_key="test_sessions.id", primary_key=True)
    athlete_id: int = Field(foreign_key="athletes.id", primary_key=True)
    test_id: str = Field(foreign_key="tests.id", primary_key=True)
    raw_value: str
