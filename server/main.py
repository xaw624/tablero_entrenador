"""Punto de entrada FastAPI: middlewares, routers, estáticos del SPA y fallback."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from server.config import settings
from server.db import init_db
from server.routers import (
    athletes,
    auth as auth_router,
    csvio,
    export,
    levels,
    patterns,
    progress,
    routines,
    sessions,
    tests,
    uploads,
)
from server.routers.uploads import uploads_dir

CLIENT_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client", "dist")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Tablero del Entrenador",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

# Sesión firmada por cookie httpOnly. samesite=lax y secure según entorno.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    https_only=settings.cookie_secure,
    same_site="lax",
    session_cookie="te_session",
    max_age=60 * 60 * 24 * 30,  # 30 días
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


# --- API ---
app.include_router(auth_router.router)
app.include_router(patterns.router)
app.include_router(levels.router)
app.include_router(athletes.router)
app.include_router(routines.router)
app.include_router(tests.router)
app.include_router(sessions.router)
app.include_router(progress.router)
app.include_router(export.router)
app.include_router(uploads.router)
app.include_router(csvio.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Medios subidos (imágenes/gifs de ejercicios) ---
app.mount("/media", StaticFiles(directory=uploads_dir()), name="media")

# --- SPA estática (build de Vite) ---
if os.path.isdir(os.path.join(CLIENT_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(CLIENT_DIST, "assets")), name="assets")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    """Cualquier ruta no-/api devuelve index.html para que el router del SPA la maneje."""
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "No encontrado"}, status_code=404)

    # Archivos sueltos en la raíz del build (favicon, manifest, fuentes, etc.)
    candidate = os.path.normpath(os.path.join(CLIENT_DIST, full_path))
    if full_path and candidate.startswith(CLIENT_DIST) and os.path.isfile(candidate):
        return FileResponse(candidate)

    index = os.path.join(CLIENT_DIST, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse(
        {"detail": "Frontend no compilado. Ejecuta `cd client && npm run build`."},
        status_code=503,
    )
