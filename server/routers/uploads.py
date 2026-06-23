"""Subida de imágenes/gifs para los medios de ejercicios.

Los archivos se guardan en data/uploads/ y se sirven en /media/<archivo> (ver main.py).
Para video se usa una URL externa, no este endpoint.
"""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from server.auth import require_user
from server.config import settings

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

# Solo imágenes/gif. Los videos van por URL externa.
ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def uploads_dir() -> str:
    # Junto a la base de datos: data/uploads
    base = os.path.dirname(os.path.abspath(settings.db_path))
    path = os.path.join(base, "uploads")
    os.makedirs(path, exist_ok=True)
    return path


@router.post("")
async def upload(file: UploadFile = File(...), _=Depends(require_user)):
    ext = ALLOWED.get(file.content_type or "")
    if not ext:
        raise HTTPException(status_code=400, detail="Formato no permitido. Usa JPG, PNG, GIF o WebP.")

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="El archivo supera 5 MB.")
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío.")

    name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(uploads_dir(), name), "wb") as fh:
        fh.write(data)
    return {"url": f"/media/{name}"}
