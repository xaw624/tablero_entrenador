"""Pruebas de sesiones (ignora vacíos / dedup) y progreso (orden + num) (§6.7, §6.8)."""


def _athlete_id(auth, name="Alumno 1"):
    athletes = auth.get("/api/athletes").json()
    return next(a["id"] for a in athletes if a["name"] == name)


def test_post_session_ignores_empty_and_dedups(auth):
    aid = _athlete_id(auth)
    aid2 = _athlete_id(auth, "Alumno 2")
    payload = {
        "date": 1700000000000,
        "note": "",
        "measurements": [
            {"athlete_id": aid, "test_id": "flex", "raw_value": "20"},
            {"athlete_id": aid, "test_id": "flex", "raw_value": "22"},  # dup → último gana
            {"athlete_id": aid2, "test_id": "flex", "raw_value": ""},     # vacío → ignorar
        ],
    }
    created = auth.post("/api/sessions", json=payload).json()
    ms = {(m["athlete_id"], m["test_id"]): m["raw_value"] for m in created["measurements"]}
    assert ms[(aid, "flex")] == "22"
    assert (aid2, "flex") not in ms


def test_progress_orders_by_date_and_converts_num(auth):
    aid = _athlete_id(auth, "Yo")
    # Inserta en orden no cronológico para verificar el orden por fecha.
    auth.post("/api/sessions", json={
        "date": 1720000000000, "measurements": [{"athlete_id": aid, "test_id": "v700", "raw_value": "3:10"}],
    })
    auth.post("/api/sessions", json={
        "date": 1710000000000, "measurements": [{"athlete_id": aid, "test_id": "v700", "raw_value": "3:30"}],
    })
    prog = auth.get(f"/api/progress?athlete_id={aid}&test_id=v700").json()
    dates = [p["date"] for p in prog["points"]]
    assert dates == sorted(dates)
    # mm:ss → segundos
    nums = [p["num"] for p in prog["points"]]
    assert nums[0] == 210.0 and nums[1] == 190.0


def test_latest_session_returns_measurements(auth):
    aid = _athlete_id(auth)
    auth.post("/api/sessions", json={
        "date": 1730000000000, "measurements": [{"athlete_id": aid, "test_id": "salto", "raw_value": "40"}],
    })
    latest = auth.get("/api/sessions/latest").json()
    assert latest is not None
    assert any(m["test_id"] == "salto" for m in latest["measurements"])
