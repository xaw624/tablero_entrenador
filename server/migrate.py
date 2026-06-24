"""Aplica las migraciones de esquema y reporta el estado de los ejercicios.

Ejecutar en el servidor con:  python -m server.migrate

Es idempotente y seguro de re-ejecutar. Convierte una BD con niveles A/B/C a niveles
con nombre (Principiante/Intermedio/Avanzado) y copia las variantes ya planteadas de cada
ejercicio a la tabla `exercise_variants`. No borra datos.
"""
from __future__ import annotations

import sys

from sqlmodel import Session, select

from server.db import engine, init_db
from server.models import ExerciseVariant, Level, RoutineDay, RoutineExercise


def run() -> None:
    print("Aplicando migraciones (idempotente)...")
    init_db()  # crea tablas/columnas nuevas y migra variantes/weekday

    with Session(engine) as session:
        levels = session.exec(select(Level).order_by(Level.sort)).all()
        exercises = session.exec(select(RoutineExercise)).all()
        with_variants = {v.exercise_id for v in session.exec(select(ExerciseVariant)).all()}
        days = session.exec(select(RoutineDay)).all()

        missing = [e.id for e in exercises if e.id not in with_variants]

        print(f"  Niveles: {len(levels)} -> {', '.join(l.label for l in levels) or '(ninguno)'}")
        print(f"  Días: {len(days)}  ({sum(1 for d in days if d.weekday is not None)} con día de calendario)")
        print(f"  Ejercicios: {len(exercises)}")
        print(f"    con variantes migradas: {len(exercises) - len(missing)}")
        if missing:
            print(f"    SIN variantes (revisar): {missing}")
        else:
            print("    todos los ejercicios tienen variantes. OK")

    print("Migración aplicada.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"Error en la migración: {e}", file=sys.stderr)
        sys.exit(1)
