# Tablero del Entrenador

Webapp **monousuario y autoalojada** para gestionar un método de entrenamiento funcional de niveles mixtos (sistema A/B/C **por patrón de movimiento**). El entrenador es el único usuario: consulta la rutina del día con la variante correcta por alumno, registra mediciones en días de prueba, ve deltas y gráficas de progreso, y exporta resúmenes.

> Especificación funcional completa: [`ESPECIFICACION_Tablero_Entrenador.md`](ESPECIFICACION_Tablero_Entrenador.md).

## Stack

- **Backend:** Python 3.12 · FastAPI · SQLModel · SQLite (WAL) · Uvicorn.
- **Frontend:** React 18 · Vite (SPA servida por el propio FastAPI → single origin, sin CORS).
- **Auth:** sesión server-side con cookie firmada httpOnly (`SessionMiddleware`) + bcrypt. Un solo usuario, creado por seed.
- **Deploy:** VM (Ubuntu) · systemd (Uvicorn) · **nginx** (reverse proxy + TLS Let's Encrypt) detrás de **Cloudflare en modo nube gris / DNS only**.

## Arranque rápido (desarrollo local)

```bash
# 1. Backend
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edita SESSION_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD; pon COOKIE_SECURE=false
python -m server.seed       # crea admin + datos semilla (idempotente)

# 2. Frontend (build servido por FastAPI)
cd client && npm install && npm run build && cd ..

# 3. Servir
uvicorn server.main:app --host 127.0.0.1 --port 8091 --reload
# abre http://127.0.0.1:8091
```

Para desarrollo del frontend con hot-reload: `cd client && npm run dev` (Vite proxya `/api` al backend).

## Funciones destacadas

- **A/B/C por patrón**: cada alumno tiene su nivel por patrón; la app resuelve la variante por ejercicio.
- **Medios por variante**: imagen/gif subida (en `data/uploads/`) o enlace de video (YouTube/Vimeo/mp4).
  Botón **"Mostrar ejercicio"** → página completa con el medio y navegación anterior/siguiente.
- **Import/Export CSV** de rutinas y pruebas (editable en Excel; importar reemplaza todo).
- **PWA instalable** con logo propio (pesa + figura corriendo): "Añadir a pantalla de inicio".
- **Mobile-first** con barra de navegación inferior.

> Para regenerar los iconos de la PWA tras editar `client/public/icons/logo.svg`: `cd client && npm run icons`.

## Documentación

- **Despliegue:** [`deploy/README-deploy.md`](deploy/README-deploy.md)
- **Pruebas / verificación:** [`docs/PRUEBAS.md`](docs/PRUEBAS.md)
- **Plan y decisiones de arquitectura:** [`docs/PLAN-Y-DECISIONES.md`](docs/PLAN-Y-DECISIONES.md)

## Tests

```bash
pytest
```

## Concepto central

Un alumno **no tiene "un nivel"**: tiene un nivel A/B/C **por cada patrón** (`empuje`, `traccion`, `pierna`, `carrera`, `core`). La app resuelve, para cada ejercicio, la variante que le toca a cada alumno según su nivel en el patrón de ese ejercicio.
