"""Pruebas de autenticación y acceso protegido (§6.2)."""


def test_health_open(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_protected_without_session_is_401(client):
    assert client.get("/api/athletes").status_code == 401


def test_login_failure(client):
    r = client.post("/api/auth/login", json={"email": "coach@test.com", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciales inválidas"


def test_login_success_and_me(auth):
    me = auth.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "coach@test.com"


def test_logout_clears_session(auth):
    auth.post("/api/auth/logout")
    assert auth.get("/api/auth/me").status_code == 401
