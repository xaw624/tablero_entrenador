"""Pruebas de alumnos y niveles por patrón (§6.4)."""


def test_seeded_athletes_have_levels(auth):
    athletes = auth.get("/api/athletes").json()
    names = {a["name"] for a in athletes}
    assert {"Alumno 1", "Alumno 2", "Alumno 3", "Alumno 4", "Yo"} <= names
    a3 = next(a for a in athletes if a["name"] == "Alumno 3")
    assert a3["levels"]["pierna"] == "C"
    assert a3["levels"]["traccion"] == "B"


def test_create_athlete_defaults_to_A(auth):
    created = auth.post("/api/athletes", json={"name": "Nuevo Tester"}).json()
    assert all(v == "A" for v in created["levels"].values())


def test_put_levels_updates(auth):
    a = auth.post("/api/athletes", json={"name": "Niveles Tester"}).json()
    r = auth.put(f"/api/athletes/{a['id']}/levels", json={"pierna": "C", "empuje": "B"})
    levels = r.json()["levels"]
    assert levels["pierna"] == "C" and levels["empuje"] == "B"


def test_put_levels_rejects_invalid_level(auth):
    a = auth.post("/api/athletes", json={"name": "Inválido Tester"}).json()
    r = auth.put(f"/api/athletes/{a['id']}/levels", json={"pierna": "Z"})
    assert r.status_code == 400


def test_soft_delete_archives(auth):
    a = auth.post("/api/athletes", json={"name": "A Archivar"}).json()
    auth.delete(f"/api/athletes/{a['id']}")
    visible = [x["id"] for x in auth.get("/api/athletes").json()]
    assert a["id"] not in visible
    all_ids = [x["id"] for x in auth.get("/api/athletes?include_archived=true").json()]
    assert a["id"] in all_ids
