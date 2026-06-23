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


def _migrate(connection) -> None:
    """Migraciones aditivas idempotentes (SQLite). create_all no altera tablas existentes."""
    existing = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(routine_exercises)")}
    for col in ("media_a", "media_b", "media_c"):
        if col not in existing:
            connection.exec_driver_sql(
                f"ALTER TABLE routine_exercises ADD COLUMN {col} TEXT NOT NULL DEFAULT ''"
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
