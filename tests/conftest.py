"""Configuración de pytest: entorno aislado y datos sembrados una vez por sesión."""
import os
import pathlib

# El entorno debe fijarse ANTES de importar server.* (config/engine se evalúan al importar).
os.environ["SESSION_SECRET"] = "test-secret-test-secret-test-secret-0123456789"
os.environ["COOKIE_SECURE"] = "false"
os.environ["APP_ENV"] = "dev"
os.environ["DB_PATH"] = "./data/_pytest.db"
os.environ["ADMIN_EMAIL"] = "coach@test.com"
os.environ["ADMIN_PASSWORD"] = "secret123"

# DB limpia en cada corrida.
for _ext in ("", "-wal", "-shm"):
    _p = pathlib.Path(os.environ["DB_PATH"] + _ext)
    if _p.exists():
        _p.unlink()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from server import seed  # noqa: E402
from server.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _seed_once():
    seed.run()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(client):
    r = client.post("/api/auth/login", json={"email": "coach@test.com", "password": "secret123"})
    assert r.status_code == 200
    return client
