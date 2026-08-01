"""Import del catálogo de ejercicios desde wger a la BD local (ver docs/CATALOGO-EJERCICIOS.md).

De una sola vez y sin dependencia en runtime: la app no llama a wger al ejecutarse. Idempotente
(upsert por id). Espeja las imágenes a data/uploads/ y guarda la ruta local /media/<archivo>.

Uso:
    python -m server.import_catalog --limit 50    # prueba
    python -m server.import_catalog               # completo
    python -m server.import_catalog --no-images   # solo texto (sin descargar imágenes)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from html import unescape

import httpx
from sqlmodel import Session

from server.auth import now_ms
from server.db import engine, init_db
from server.models import ExerciseCatalog
from server.routers.uploads import uploads_dir
from server.services import normalize

WGER_BASE = "https://wger.de/api/v2"
PAGE_SIZE = 100

# Mapeo categoría de wger → patrón del tablero (empuje/traccion/pierna/carrera/core).
# 'Arms' queda sin asignar a propósito (bíceps=tracción vs tríceps=empuje, ambiguo).
CATEGORY_TO_PATTERN: dict[str, str | None] = {
    "Chest": "empuje",
    "Shoulders": "empuje",
    "Back": "traccion",
    "Legs": "pierna",
    "Calves": "pierna",
    "Abs": "core",
    "Cardio": "carrera",
    "Arms": None,
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(html: str) -> str:
    """HTML de wger → texto plano legible."""
    text = _TAG_RE.sub(" ", html or "")
    return _WS_RE.sub(" ", unescape(text)).strip()


def resolve_language_id(client: httpx.Client, short_name: str) -> int:
    data = client.get(f"{WGER_BASE}/language/", params={"limit": 100}).raise_for_status().json()
    for lang in data["results"]:
        if lang["short_name"] == short_name:
            return lang["id"]
    raise SystemExit(f"No se encontró el idioma '{short_name}' en la API de wger.")


def pick_translation(translations: list[dict], lang_id: int) -> tuple[dict | None, bool]:
    """Devuelve (traducción, es_idioma_pedido). Prefiere el idioma pedido; si no, la primera."""
    for t in translations:
        if t.get("language") == lang_id and (t.get("name") or "").strip():
            return t, True
    for t in translations:
        if (t.get("name") or "").strip():
            return t, False
    return None, False


def download_image(client: httpx.Client, url: str, ex_id: str) -> str:
    """Descarga la imagen a data/uploads/ (idempotente) y devuelve la ruta /media/<archivo>."""
    ext = os.path.splitext(url.split("?")[0])[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        ext = ".jpg"
    filename = f"catalog-{ex_id}{ext}"
    dest = os.path.join(uploads_dir(), filename)
    if not os.path.exists(dest):
        resp = client.get(url, timeout=60)
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            fh.write(resp.content)
    return f"/media/{filename}"


def main_image_url(images: list[dict]) -> str | None:
    if not images:
        return None
    for img in images:
        if img.get("is_main") and img.get("image"):
            return img["image"]
    for img in images:
        if img.get("image"):
            return img["image"]
    return None


def build_record(
    client: httpx.Client, item: dict, lang_id: int, download: bool
) -> tuple[ExerciseCatalog | None, bool, bool]:
    """(registro, es_es, tiene_imagen). Devuelve (None, ...) si no hay traducción usable."""
    translation, is_target_lang = pick_translation(item.get("translations", []), lang_id)
    if not translation:
        return None, False, False

    ex_id = f"wger-{item['id']}"
    name = translation["name"].strip()
    category = (item.get("category") or {}).get("name", "")
    muscles = ", ".join(m.get("name_en") or m.get("name", "") for m in item.get("muscles", []))
    equipment = ", ".join(e.get("name", "") for e in item.get("equipment", []))
    lic = item.get("license") or {}

    media = ""
    if download:
        url = main_image_url(item.get("images", []))
        if url:
            try:
                media = download_image(client, url, ex_id)
            except httpx.HTTPError as e:
                print(f"  [!] imagen falló para {ex_id}: {e}", file=sys.stderr)

    record = ExerciseCatalog(
        id=ex_id,
        name=name,
        name_norm=normalize(name),
        pattern_id=CATEGORY_TO_PATTERN.get(category),
        category=category,
        equipment=equipment,
        muscles=muscles,
        instructions=strip_html(translation.get("description", "")),
        media=media,
        source="wger",
        attribution=(lic.get("license_author") or item.get("license_author") or "wger.de"),
        license_name=lic.get("short_name", ""),
        created_at=now_ms(),
    )
    return record, is_target_lang, bool(media)


def upsert(session: Session, record: ExerciseCatalog) -> None:
    existing = session.get(ExerciseCatalog, record.id)
    if existing:
        data = record.model_dump(exclude={"id", "created_at"})
        for key, value in data.items():
            setattr(existing, key, value)
        session.add(existing)
    else:
        session.add(record)


def run(limit: int | None, download: bool, short_name: str) -> None:
    init_db()
    total = imported = with_image = es_count = 0

    with httpx.Client(headers={"User-Agent": "tablero_entrenador/import_catalog"}) as client:
        lang_id = resolve_language_id(client, short_name)
        print(f"Idioma '{short_name}' = id {lang_id}. Descargando catálogo de wger...")

        url: str | None = f"{WGER_BASE}/exerciseinfo/"
        params: dict | None = {"limit": PAGE_SIZE}
        with Session(engine) as session:
            while url:
                page = client.get(url, params=params, timeout=60).raise_for_status().json()
                params = None  # 'next' ya trae los query params
                for item in page["results"]:
                    total += 1
                    record, is_es, has_img = build_record(client, item, lang_id, download)
                    if not record:
                        continue
                    upsert(session, record)
                    imported += 1
                    es_count += int(is_es)
                    with_image += int(has_img)
                    if limit and imported >= limit:
                        url = None
                        break
                else:
                    url = page.get("next")
                    continue
                break
            session.commit()

    print("\n--- Resumen del import ---")
    print(f"  Ejercicios vistos en la API : {total}")
    print(f"  Importados (con traducción) : {imported}")
    print(f"  En español ('{short_name}')        : {es_count}")
    print(f"  Con imagen espejada         : {with_image}" if download else "  Imágenes: omitidas (--no-images)")
    print("Import completo.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Importa el catálogo de ejercicios desde wger.")
    p.add_argument("--limit", type=int, default=None, help="Máximo de ejercicios a importar (prueba).")
    p.add_argument("--no-images", action="store_true", help="No descargar imágenes (solo texto).")
    p.add_argument("--lang", default="es", help="short_name del idioma (por defecto 'es').")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    try:
        run(limit=args.limit, download=not args.no_images, short_name=args.lang)
    except (httpx.HTTPError, OSError) as e:
        print(f"Error en el import: {e}", file=sys.stderr)
        sys.exit(1)
