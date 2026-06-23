"""Pruebas de iteración 2: subida de medios, /media, migración y CSV import/export."""
from sqlalchemy import inspect

from server.db import engine

# PNG 1x1 válido.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)


def test_migration_added_media_columns():
    cols = {c["name"] for c in inspect(engine).get_columns("routine_exercises")}
    assert {"media_a", "media_b", "media_c"} <= cols


def test_upload_rejects_non_image(auth):
    r = auth.post("/api/uploads", files={"file": ("x.txt", b"hola", "text/plain")})
    assert r.status_code == 400


def test_upload_image_and_serve(auth):
    r = auth.post("/api/uploads", files={"file": ("p.png", PNG, "image/png")})
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert url.startswith("/media/")
    served = auth.get(url)
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/")


def test_media_propagates_to_for_athlete(auth):
    routines = auth.get("/api/routines").json()
    ex = routines["lunes"]["blocks"][0]["items"][0]
    auth.patch(f"/api/routines/exercises/{ex['id']}", json={"media_c": "https://youtu.be/abc123"})
    athletes = auth.get("/api/athletes").json()
    a3 = next(a for a in athletes if a["name"] == "Alumno 3")  # empuje: C
    fa = auth.get(f"/api/routines/lunes/for-athlete/{a3['id']}").json()
    item = fa["blocks"][0]["items"][0]
    assert item["level"] == "C"
    assert item["media"] == "https://youtu.be/abc123"


def test_export_routines_csv_has_bom_and_media(auth):
    r = auth.get("/api/export/routines.csv")
    assert r.status_code == 200
    assert r.text.startswith("﻿")  # BOM para Excel
    assert "day_key" in r.text and "media_a" in r.text


def test_import_routines_replace_and_validate(auth):
    csv = (
        "day_key,day_name,day_focus,block_title,block_sort,exercise_name,pattern_id,"
        "variant_a,variant_b,variant_c,media_a,media_b,media_c,exercise_sort\r\n"
        "lunes,Lunes,Test Focus,Bloque X,1,Ej Uno,empuje,a,b,c,,,,1\r\n"
    )
    r = auth.post("/api/import/routines.csv", files={"file": ("rutinas.csv", csv.encode("utf-8-sig"), "text/csv")})
    assert r.status_code == 200, r.text
    routines = auth.get("/api/routines").json()
    assert routines["lunes"]["focus"] == "Test Focus"
    assert routines["lunes"]["blocks"][0]["items"][0]["name"] == "Ej Uno"


def test_import_routines_rejects_bad_pattern(auth):
    csv = "day_key,block_title,exercise_name,pattern_id\r\nlunes,B,Ej,PATRON_MALO\r\n"
    r = auth.post("/api/import/routines.csv", files={"file": ("r.csv", csv.encode(), "text/csv")})
    assert r.status_code == 400


def test_import_tests_semicolon_delimiter(auth):
    csv = "id;name;pattern_id;unit;better;sort\r\n;Salto Nuevo;pierna;cm;high;9\r\n"
    r = auth.post("/api/import/tests.csv", files={"file": ("pruebas.csv", csv.encode("utf-8-sig"), "text/csv")})
    assert r.status_code == 200, r.text
    names = {t["name"] for t in auth.get("/api/tests").json()}
    assert "Salto Nuevo" in names
