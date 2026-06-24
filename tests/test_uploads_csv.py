"""Pruebas de subida de medios y CSV (it.2) adaptadas a niveles dinámicos (it.3)."""

# PNG 1x1 válido.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)


def test_levels_seeded(auth):
    levels = auth.get("/api/levels").json()
    assert [l["label"] for l in levels] == ["Principiante", "Intermedio", "Avanzado"]


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


def test_variant_media_propagates_to_for_athlete(auth):
    routines = auth.get("/api/routines").json()
    ex = routines["lunes"]["blocks"][0]["items"][0]
    # Asigna medio a la variante C (Avanzado) vía el endpoint de variantes.
    auth.put(f"/api/routines/exercises/{ex['id']}/variants/C", json={"media": "https://youtu.be/abc123"})
    athletes = auth.get("/api/athletes").json()
    a3 = next(a for a in athletes if a["name"] == "Alumno 3")  # empuje: C
    fa = auth.get(f"/api/routines/lunes/for-athlete/{a3['id']}").json()
    item = fa["blocks"][0]["items"][0]
    assert item["level"] == "C"
    assert item["media"] == "https://youtu.be/abc123"


def test_export_routines_csv_has_bom_and_level_columns(auth):
    r = auth.get("/api/export/routines.csv")
    assert r.status_code == 200
    assert r.text.startswith("﻿")  # BOM para Excel
    head = r.text.splitlines()[0]
    assert "day_key" in head and "weekday" in head
    assert "var_A" in head and "media_A" in head  # columnas dinámicas por nivel


def test_import_routines_replace_and_validate(auth):
    csv = (
        "day_key,day_name,weekday,day_focus,day_sort,block_title,block_sort,"
        "exercise_name,pattern_id,exercise_sort,var_A,media_A,var_B,media_B,var_C,media_C\r\n"
        "lunes,Lunes,1,Test Focus,1,Bloque X,1,Ej Uno,empuje,1,Texto A,,Texto B,,Texto C,\r\n"
    )
    r = auth.post("/api/import/routines.csv", files={"file": ("rutinas.csv", csv.encode("utf-8-sig"), "text/csv")})
    assert r.status_code == 200, r.text
    routines = auth.get("/api/routines").json()
    assert routines["lunes"]["focus"] == "Test Focus"
    item = routines["lunes"]["blocks"][0]["items"][0]
    assert item["name"] == "Ej Uno"
    assert item["variants"]["A"]["text"] == "Texto A"


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
