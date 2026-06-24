"""Engine SQLite, inicialización del esquema y dependencia de sesión."""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from server.config import settings

# Importar models para que SQLModel registre las tablas antes de create_all().
from server import models  # noqa: F401  (efecto: registra metadata)


def _ensure_db_dir(db_path: str) -> None:
    directory = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(directory, exist_ok=True)


_ensure_db_dir(settings.db_path)

# check_same_thread=False: necesario porque FastAPI usa varios hilos con SQLite.
engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
    """WAL para mejor concurrencia lectura/escritura; foreign_keys ON para integridad."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


# Niveles por defecto: mapean A/B/C heredados a nombres legibles, conservando sus colores.
_DEFAULT_LEVELS = [
    ("A", "Principiante", "#d8472b", 1),
    ("B", "Intermedio", "#e6a02c", 2),
    ("C", "Avanzado", "#3fae7a", 3),
]
_WEEKDAY_BY_KEY = {
    "domingo": 0, "lunes": 1, "martes": 2, "miercoles": 3,
    "jueves": 4, "viernes": 5, "sabado": 6,
}


def _columns(connection, table: str) -> set[str]:
    return {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")}


def _migrate(connection) -> None:
    """Migraciones idempotentes (SQLite). create_all crea tablas nuevas pero no altera existentes.

    Iteración 3: niveles dinámicos (catálogo `levels` + `exercise_variants`) y `weekday` en días.
    Convierte una BD con columnas legacy variant_a/b/c (+ media_a/b/c) sin pérdida.
    """
    # 1. routine_days.weekday (ALTER si la columna falta en una BD existente).
    day_cols = _columns(connection, "routine_days")
    if day_cols and "weekday" not in day_cols:
        connection.exec_driver_sql("ALTER TABLE routine_days ADD COLUMN weekday INTEGER")

    # 2. Niveles por defecto si el catálogo está vacío.
    if not connection.exec_driver_sql("SELECT COUNT(*) FROM levels").scalar():
        for lid, label, color, sort in _DEFAULT_LEVELS:
            connection.exec_driver_sql(
                "INSERT INTO levels (id, label, color, sort) VALUES (?, ?, ?, ?)",
                (lid, label, color, sort),
            )

    # 3. Copiar variantes legacy → exercise_variants. Idempotente y auto-sanador:
    #    copia SOLO los ejercicios que aún no tienen ninguna fila de variante, así
    #    repara estados parciales (p. ej. si una corrida anterior quedó a medias).
    ex_cols = _columns(connection, "routine_exercises")
    if "variant_a" in ex_cols:
        has_media = "media_a" in ex_cols
        with_variants = {
            row[0] for row in connection.exec_driver_sql(
                "SELECT DISTINCT exercise_id FROM exercise_variants"
            )
        }
        cols = "id, variant_a, variant_b, variant_c"
        if has_media:
            cols += ", media_a, media_b, media_c"
        rows = connection.exec_driver_sql(f"SELECT {cols} FROM routine_exercises").all()
        for r in rows:
            if r[0] in with_variants:
                continue  # ya migrado
            texts = {"A": r[1] or "", "B": r[2] or "", "C": r[3] or ""}
            medias = {"A": r[4] or "", "B": r[5] or "", "C": r[6] or ""} if has_media else {}
            for lid in ("A", "B", "C"):
                connection.exec_driver_sql(
                    "INSERT INTO exercise_variants (exercise_id, level_id, text, media) "
                    "VALUES (?, ?, ?, ?)",
                    (r[0], lid, texts[lid], medias.get(lid, "")),
                )

    # 4. Poblar weekday por day_key conocido si todos están en NULL.
    total = connection.exec_driver_sql("SELECT COUNT(*) FROM routine_days").scalar()
    nulls = connection.exec_driver_sql(
        "SELECT day_key FROM routine_days WHERE weekday IS NULL"
    ).all()
    if total and len(nulls) == total:
        for (dk,) in nulls:
            wd = _WEEKDAY_BY_KEY.get(dk)
            if wd is not None:
                connection.exec_driver_sql(
                    "UPDATE routine_days SET weekday = ? WHERE day_key = ?", (wd, dk)
                )


def init_db() -> None:
    """Crea las tablas que falten y aplica migraciones aditivas (idempotente)."""
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        _migrate(connection)


def get_session() -> Iterator[Session]:
    """Dependency de FastAPI: una sesión por request."""
    with Session(engine) as session:
        yield session
