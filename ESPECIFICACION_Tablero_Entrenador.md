# Especificación para implementación — Tablero del Entrenador

> **Documento de implementación para un agente de código.** Stack: Python 3.12 + FastAPI + SQLModel + SQLite (backend), React 18 + Vite (frontend), systemd + **nginx** (TLS Let's Encrypt) detrás de **Cloudflare en modo nube gris / DNS only** en VM Ubuntu (deploy). Webapp monousuario, autoalojada.
>
> **Nota de versión:** el despliegue se actualizó de Caddy a **nginx + Cloudflare nube gris**; ver ADR-6 en §3 y la guía [`deploy/README-deploy.md`](deploy/README-deploy.md). Decisiones detalladas en [`docs/PLAN-Y-DECISIONES.md`](docs/PLAN-Y-DECISIONES.md).

## Índice
1. Resumen ejecutivo · Contexto del dominio · Alcance · ADR · Arquitectura  →  *Parte 1*
2. Modelo de datos · API REST · Lógica de negocio  →  *Parte 2*
3. Frontend: vistas, comportamiento, diseño  →  *Parte 3*
4. Datos semilla · Config · Seguridad · Deploy · Criterios de aceptación · Roadmap · Preguntas abiertas  →  *Parte 4*

---

# Especificación Técnica — Tablero del Entrenador (Método Funcional)

**Versión del documento:** 2.0 (stack Python / FastAPI)
**Audiencia:** Agente de código (implementación autónoma) + dueño del proyecto.
**Objetivo:** Construir una webapp personal, autoalojada, para que un entrenador consulte rutinas diarias, evalúe a sus alumnos en días de prueba y siga su progreso. Un solo usuario operador (el entrenador). Los alumnos NO acceden a la app.

---

## 0. Resumen ejecutivo

El Tablero del Entrenador es una aplicación web monousuario para gestionar un método de entrenamiento funcional de niveles mixtos (sistema A/B/C). El entrenador es el único que inicia sesión. Gestiona un grupo reducido de alumnos (5–12), cada uno con un nivel independiente por patrón de movimiento. La app muestra la rutina del día con la variante correcta por alumno, permite registrar mediciones en días de prueba, calcula deltas contra pruebas previas, grafica el progreso y exporta/comparte resúmenes (para enviar a los alumnos por fuera de la app, p. ej. WhatsApp).

**Stack (definido por el dueño + recomendaciones):**
- **Backend: Python 3.12 + FastAPI + SQLModel** (SQLAlchemy core + Pydantic) sobre **SQLite** (archivo, sin servidor de BD aparte). Servidor ASGI **Uvicorn**.
- **Frontend: React 18 + Vite** (SPA). El build estático lo sirve el propio FastAPI (single origin, sin CORS).
- **Auth:** sesión server-side con cookie firmada httpOnly (Starlette `SessionMiddleware`) + `passlib[bcrypt]`. Un solo usuario, creado por script de seed.
- **Deploy:** VM Ubuntu + **systemd** (proceso Uvicorn) + **nginx** (reverse proxy, TLS Let's Encrypt vía certbot) detrás de **Cloudflare en modo nube gris (DNS only)**. nginx reverse-proxya a Uvicorn; FastAPI sigue sirviendo el build estático (single origin). _(Antes: Caddy; ver ADR-6.)_

**Principio de diseño:** todo autocontenido, cero dependencias de servicios externos de pago, despliegue reproducible, mantenible en Python.

---

## 1. Contexto del dominio (imprescindible leer antes de codear)

### 1.1 El sistema A/B/C
Cada ejercicio se define en tres variantes de dificultad:
- **A — Base:** regresión del movimiento; control y rango.
- **B — Intermedio:** patrón completo; volumen moderado.
- **C — Avanzado:** variante difícil o con carga; tempo, lastre, potencia.

### 1.2 Niveles por PATRÓN, no globales (regla central del producto)
Un alumno NO tiene "un nivel". Tiene un nivel A/B/C **por cada patrón de movimiento**. Patrones canónicos:

| id | Etiqueta | sort |
|----|----------|------|
| `empuje` | Empuje | 1 |
| `traccion` | Tracción | 2 |
| `pierna` | Pierna | 3 |
| `carrera` | Carrera | 4 |
| `core` | Core | 5 |

Ejemplo: un alumno puede ser nivel **C en pierna** y **A en tracción** simultáneamente. Esta es la característica diferenciadora del producto; ninguna app comercial la maneja bien. Debe implementarse con rigor: el nivel es siempre `(alumno, patrón) → A|B|C`.

### 1.3 Cómo se resuelve la variante mostrada (algoritmo nuclear)
Cada ejercicio de una rutina está etiquetado con un `pattern_id`. Para mostrar a un alumno concreto qué le toca en ese ejercicio:

```
nivel  = alumno.levels[ejercicio.pattern_id]      # 'A' | 'B' | 'C'
texto  = ejercicio["variant_" + nivel.lower()]    # variant_a | variant_b | variant_c
```

Si faltara el nivel para ese patrón (no debería tras el seed), usar 'A' como fallback seguro.

### 1.4 Rutina semanal
Cinco días (lunes–viernes), cada uno con un `focus` y patrones primarios. Cada día tiene bloques ordenados; cada bloque tiene ejercicios ordenados; cada ejercicio tiene `name`, `pattern_id`, y tres textos `variant_a/b/c`. Datos semilla completos en §7.

### 1.5 Pruebas de evaluación
Batería de pruebas, cada una ligada a un patrón, con unidad y dirección de mejora:

| id | Nombre | pattern | unit | better |
|----|--------|---------|------|--------|
| `flex` | Flexiones máximas | empuje | reps | high |
| `dom` | Dominadas / remos máx. | traccion | reps | high |
| `v700` | Vuelta 700 m | carrera | mm:ss | low |
| `salto` | Salto vertical | pierna | cm | high |
| `plancha` | Plancha / hollow máx. | core | seg | high |

- `unit` ∈ {`reps`, `seg`, `cm`, `kg`, `m`, `mm:ss`}.
- `better` ∈ {`high`, `low`}: define si mayor o menor es mejora. Determina el color del delta y la lectura de la gráfica.
- `mm:ss` se **almacena** como texto "m:ss" y se **compara** convertido a segundos.

### 1.6 Periodización (contexto; opcional en v1)
El método usa bloques de 4 semanas (3 carga + 1 descarga). Un indicador de "semana del bloque" es deseable pero NO bloqueante para v1 (ver §9 Roadmap).

---

## 2. Alcance

### 2.1 Dentro de alcance (v1)
1. Login del entrenador (un solo usuario).
2. Vista "Hoy": rutina del día seleccionable, con dos modos:
   - **Todos:** muestra las 3 variantes A/B/C de cada ejercicio.
   - **Por alumno:** muestra solo la variante que corresponde a ese alumno según su nivel en el patrón del ejercicio.
3. Gestión de alumnos: crear, renombrar, archivar, fijar nivel A/B/C por patrón.
4. Día de prueba: elegir fecha, elegir prueba, capturar valores de todos los alumnos, ver delta vs. prueba anterior, guardar sesión.
5. Compartir/exportar resumen de una sesión (texto plano + CSV).
6. Progreso: gráfica de evolución por alumno + prueba, con historial y tendencia.
7. Editor de rutinas: días, bloques, ejercicios, variantes, reasignar patrón, reordenar.
8. Editor de pruebas: batería (nombre, patrón, unidad, dirección).
9. Persistencia en servidor (SQLite), accesible desde móvil y laptop tras login.

### 2.2 Fuera de alcance (v1)
- Acceso de alumnos / multiusuario.
- Mensajería, pagos, notificaciones push.
- App nativa (es webapp responsive; PWA opcional en §8).
- Integración con wearables.

---

## 3. Decisiones de arquitectura (ADR resumidos)

### ADR-1: SQLite en vez de Postgres/MySQL
**Contexto:** un solo usuario; datos pequeños (decenas de alumnos máx., cientos de sesiones a lo largo de años).
**Decisión:** SQLite en archivo (`data/app.db`), acceso vía SQLModel/SQLAlchemy.
**Consecuencias:** cero administración de BD; backup = copiar un archivo; despliegue trivial. Activar `PRAGMA journal_mode=WAL`. Si en el futuro hiciera falta concurrencia intensiva multiusuario, migrar a Postgres (improbable aquí).

### ADR-2: SPA React servida por FastAPI (single origin)
**Decisión:** Vite compila a `client/dist`; FastAPI monta esos estáticos y expone `/api/*`. Mismo origen → cookies de sesión sin CORS.
**Consecuencias:** un solo proceso, un solo puerto. Caddy hace TLS y proxy.

### ADR-3: Sesión con cookie httpOnly (no JWT en localStorage)
**Decisión:** `SessionMiddleware` de Starlette con cookie `httpOnly`, `secure`, `samesite=lax`, firmada con `SESSION_SECRET`. La sesión guarda solo `{"uid": <user_id>}`.
**Consecuencias:** protección frente a robo de token por XSS; logout real limpiando la sesión. Sin store externo: la cookie firmada basta para un usuario. (Si se desea revocación server-side, añadir tabla `sessions`; no requerido en v1.)

### ADR-4: Un solo usuario gestionado por seed/env
**Decisión:** tabla `users` con `email` + `password_hash` (bcrypt). El usuario inicial se crea con `python -m server.seed` leyendo `ADMIN_EMAIL` y `ADMIN_PASSWORD` del entorno. Endpoint de registro: inexistente. Endpoint para cambiar contraseña: incluido (§6.2).

### ADR-5: SQLModel como ORM
**Decisión:** SQLModel (de los autores de FastAPI) unifica modelos Pydantic y tablas SQLAlchemy, reduce boilerplate y da validación gratis.
**Consecuencias:** modelos declarados una vez; sesiones con `Session(engine)`. Migraciones simples vía SQL idempotente al arranque (v1) o Alembic si crece.

### ADR-6: nginx + Cloudflare nube gris en vez de Caddy
**Contexto:** la VM de despliegue ya hospeda otros proyectos con **nginx** multi-sitio, puertos 80/443 abiertos y **certbot** instalado; el DNS se gestiona en **Cloudflare en modo nube gris (DNS only)** y el subdominio `fitness.streamlytics.stream` ya apunta a la máquina. Caddy duplicaría el reverse proxy existente y competiría por los puertos.
**Decisión:** añadir un `server block` de nginx para el subdominio que hace `proxy_pass` a Uvicorn en `127.0.0.1:8091`. TLS lo emite **Let's Encrypt vía certbot** (challenge HTTP-01, que funciona porque en nube gris el tráfico llega directo al origen). Cloudflare actúa solo como DNS autoritativo (no proxy). FastAPI mantiene ADR-2 (sirve el build estático); nginx solo reverse-proxya.
**Consecuencias:** nginx termina TLS y proxya HTTP, por lo que envía `X-Forwarded-Proto $scheme` y Uvicorn arranca con `--proxy-headers --forwarded-allow-ips 127.0.0.1` (esquema/secure-cookie correctos). El puerto es configurable (`.env` `PORT`, default 8091) por convivencia con otros servicios. Detalles y alternativas (Tunnel, nube naranja) en [`docs/PLAN-Y-DECISIONES.md`](docs/PLAN-Y-DECISIONES.md). Archivos: [`deploy/nginx/fitness.streamlytics.stream.conf`](deploy/nginx/fitness.streamlytics.stream.conf), [`deploy/tablero-entrenador.service`](deploy/tablero-entrenador.service).

---

## 4. Arquitectura general

```
   Internet ──DNS (Cloudflare nube gris / DNS only)──► VM (IP pública)
┌─────────────────────────────────────────────────────────┐
│                       VM (Ubuntu)                        │
│                                                          │
│   :443/:80  nginx (vhost fitness.streamlytics.stream)    │
│                   │  TLS Let's Encrypt (certbot)          │
│                   │  HTTP→HTTPS, proxy + X-Forwarded-Proto│
│                   │  reverse_proxy → 127.0.0.1:8091       │
│                   ▼                                       │
│     Uvicorn + FastAPI (:8091)  ◄── systemd service        │
│       (--proxy-headers --forwarded-allow-ips 127.0.0.1)   │
│              ├── /api/*    (JSON REST)                    │
│              ├── /assets/* (estáticos del build Vite)     │
│              └── /*        (index.html SPA fallback)      │
│                   │                                       │
│                   ▼                                       │
│            SQLModel/SQLAlchemy ──► data/app.db (SQLite)   │
└─────────────────────────────────────────────────────────┘
```

### 4.1 Estructura de carpetas del repositorio
```
tablero_entrenador/          # en el servidor: /home/ubuntu/tablero_entrenador
├── server/
│   ├── __init__.py
│   ├── main.py               # crea FastAPI, middlewares, monta estáticos + SPA fallback
│   ├── config.py             # settings vía pydantic-settings (.env)
│   ├── db.py                 # engine, init_db(), get_session() dependency
│   ├── models.py             # modelos SQLModel (tablas)
│   ├── schemas.py            # modelos Pydantic de entrada/salida (DTOs)
│   ├── auth.py               # login/logout, dependency require_user, hashing
│   ├── seed.py               # crea usuario admin + datos semilla (idempotente)
│   ├── logic.py              # parseo de valores, deltas, resolución de variantes
│   └── routers/
│       ├── __init__.py
│       ├── auth.py
│       ├── athletes.py
│       ├── routines.py
│       ├── tests.py
│       ├── sessions.py       # sesiones de prueba + mediciones
│       └── export.py         # CSV / texto de resumen
├── client/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js            # wrapper fetch con credentials:'include'
│       ├── state/store.jsx   # contexto global (ver §6.7)
│       ├── pages/
│       │   ├── Login.jsx
│       │   ├── Today.jsx
│       │   ├── TestDay.jsx
│       │   ├── Progress.jsx
│       │   ├── Athletes.jsx
│       │   └── Editor.jsx
│       ├── components/       # ExerciseRow, Chart, LevelPicker, Toast, etc.
│       └── styles/tokens.css
├── deploy/
│   ├── tablero-entrenador.service
│   ├── nginx/fitness.streamlytics.stream.conf
│   ├── backup.sh
│   └── README-deploy.md
├── docs/
│   ├── PRUEBAS.md
│   └── PLAN-Y-DECISIONES.md
├── pyproject.toml            # deps backend (o requirements.txt)
├── .env.example
└── README.md
```
-e 

---

# Parte 2 — Modelo de datos, API REST y lógica de negocio

## 5. Modelo de datos

### 5.1 Esquema relacional (SQLite)
Timestamps como **epoch milliseconds (INTEGER)** para orden cronológico simple. El nivel por patrón es **relacional** (no JSON) para integridad referencial y para resolver variantes con joins limpios.

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at    INTEGER NOT NULL
);

CREATE TABLE patterns (
  id    TEXT PRIMARY KEY,           -- 'empuje','traccion','pierna','carrera','core'
  label TEXT NOT NULL,
  sort  INTEGER NOT NULL
);

CREATE TABLE athletes (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL,
  sort       INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  archived   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE athlete_levels (
  athlete_id INTEGER NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  pattern_id TEXT    NOT NULL REFERENCES patterns(id),
  level      TEXT    NOT NULL CHECK (level IN ('A','B','C')),
  PRIMARY KEY (athlete_id, pattern_id)
);

CREATE TABLE routine_days (
  day_key TEXT PRIMARY KEY,         -- 'lunes'..'viernes'
  name    TEXT NOT NULL,
  focus   TEXT NOT NULL,
  sort    INTEGER NOT NULL
);

CREATE TABLE routine_blocks (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  day_key TEXT NOT NULL REFERENCES routine_days(day_key) ON DELETE CASCADE,
  title   TEXT NOT NULL,
  sort    INTEGER NOT NULL
);

CREATE TABLE routine_exercises (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  block_id   INTEGER NOT NULL REFERENCES routine_blocks(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  pattern_id TEXT NOT NULL REFERENCES patterns(id),
  variant_a  TEXT NOT NULL DEFAULT '',
  variant_b  TEXT NOT NULL DEFAULT '',
  variant_c  TEXT NOT NULL DEFAULT '',
  sort       INTEGER NOT NULL
);

CREATE TABLE tests (
  id         TEXT PRIMARY KEY,      -- 'flex',... o slug generado
  name       TEXT NOT NULL,
  pattern_id TEXT NOT NULL REFERENCES patterns(id),
  unit       TEXT NOT NULL,         -- 'reps','seg','cm','kg','m','mm:ss'
  better     TEXT NOT NULL CHECK (better IN ('high','low')),
  sort       INTEGER NOT NULL,
  archived   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE test_sessions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  date       INTEGER NOT NULL,      -- epoch ms (mediodía local de la fecha elegida)
  note       TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL
);

CREATE TABLE measurements (
  session_id INTEGER NOT NULL REFERENCES test_sessions(id) ON DELETE CASCADE,
  athlete_id INTEGER NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  test_id    TEXT    NOT NULL REFERENCES tests(id),
  raw_value  TEXT    NOT NULL,      -- valor tal cual lo capturó el entrenador
  PRIMARY KEY (session_id, athlete_id, test_id)
);

CREATE INDEX idx_meas_athlete_test ON measurements(athlete_id, test_id);
CREATE INDEX idx_sessions_date ON test_sessions(date);
```

**Notas de modelado:**
- `raw_value` siempre TEXT. La conversión a número (deltas/gráficas) se hace en `logic.py` respetando `unit` (§6.6).
- Soft delete (`archived`) en `athletes` y `tests`: nunca borrar físicamente para preservar historial. La UI los oculta; los endpoints de listado aceptan `?include_archived=false` por defecto.
- `test_sessions.date` = fecha de la prueba (la elige el usuario). `created_at` = cuándo se guardó.

### 5.2 Modelos SQLModel (server/models.py) — esqueleto
```python
from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: int

class Pattern(SQLModel, table=True):
    id: str = Field(primary_key=True)
    label: str
    sort: int

class Athlete(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sort: int = 0
    created_at: int
    archived: int = 0

class AthleteLevel(SQLModel, table=True):
    __tablename__ = "athlete_levels"
    athlete_id: int = Field(foreign_key="athlete.id", primary_key=True)
    pattern_id: str = Field(foreign_key="pattern.id", primary_key=True)
    level: str  # 'A'|'B'|'C'

class RoutineDay(SQLModel, table=True):
    __tablename__ = "routine_days"
    day_key: str = Field(primary_key=True)
    name: str
    focus: str
    sort: int

class RoutineBlock(SQLModel, table=True):
    __tablename__ = "routine_blocks"
    id: Optional[int] = Field(default=None, primary_key=True)
    day_key: str = Field(foreign_key="routine_days.day_key")
    title: str
    sort: int

class RoutineExercise(SQLModel, table=True):
    __tablename__ = "routine_exercises"
    id: Optional[int] = Field(default=None, primary_key=True)
    block_id: int = Field(foreign_key="routine_blocks.id")
    name: str
    pattern_id: str = Field(foreign_key="pattern.id")
    variant_a: str = ""
    variant_b: str = ""
    variant_c: str = ""
    sort: int

class Test(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    pattern_id: str = Field(foreign_key="pattern.id")
    unit: str
    better: str  # 'high'|'low'
    sort: int
    archived: int = 0

class TestSession(SQLModel, table=True):
    __tablename__ = "test_sessions"
    id: Optional[int] = Field(default=None, primary_key=True)
    date: int
    note: str = ""
    created_at: int

class Measurement(SQLModel, table=True):
    session_id: int = Field(foreign_key="test_sessions.id", primary_key=True)
    athlete_id: int = Field(foreign_key="athlete.id", primary_key=True)
    test_id: str = Field(foreign_key="test.id", primary_key=True)
    raw_value: str
```

---

## 6. API REST

**Convenciones generales:**
- Prefijo `/api`. JSON en cuerpo y respuesta. Fechas en epoch ms.
- Todos los endpoints excepto `/api/auth/login` y `/api/health` requieren sesión válida (dependency `require_user`). Sin sesión → `401 {"detail":"No autenticado"}`.
- Errores con forma `{"detail": "<mensaje legible en español>"}` y código HTTP adecuado (400 validación, 404 no encontrado, 409 conflicto, 401 auth).
- Validación de entrada con Pydantic (schemas.py). `level` ∈ A/B/C; `pattern_id` debe existir; `unit`/`better` en sus enums.

### 6.1 Salud
```
GET /api/health → 200 {"status":"ok"}
```

### 6.2 Autenticación
```
POST /api/auth/login
  body: {"email": str, "password": str}
  200: {"email": str}           # set-cookie de sesión
  401: {"detail":"Credenciales inválidas"}

POST /api/auth/logout
  200: {"ok": true}             # limpia la sesión

GET  /api/auth/me
  200: {"email": str}           # usuario actual
  401 si no hay sesión

POST /api/auth/change-password   (requiere sesión)
  body: {"current": str, "next": str}
  200: {"ok": true}
  400: {"detail":"La contraseña actual no coincide"}
```
Hashing con passlib bcrypt. Rate-limit básico opcional (ver §10 seguridad).

### 6.3 Patrones (catálogo, solo lectura en v1)
```
GET /api/patterns → 200 [{"id","label","sort"}, ...]   # ordenado por sort
```

### 6.4 Alumnos
```
GET /api/athletes?include_archived=false
  200: [{"id","name","sort","archived",
         "levels": {"empuje":"B","traccion":"A","pierna":"B","carrera":"B","core":"A"}}, ...]
  # 'levels' es un dict patrón→nivel construido desde athlete_levels.

POST /api/athletes
  body: {"name": str}
  201: alumno creado, con 'levels' inicializado a 'A' en todos los patrones.

PATCH /api/athletes/{id}
  body parcial: {"name"?: str, "sort"?: int, "archived"?: 0|1}
  200: alumno actualizado.

PUT /api/athletes/{id}/levels
  body: {"empuje":"C","traccion":"A", ...}   # uno o varios patrones
  200: alumno con levels actualizado.
  # upsert en athlete_levels; valida nivel y patrón.

DELETE /api/athletes/{id}
  200: {"ok": true}   # SOFT delete → archived=1 (no borra físico para preservar historial)
```

### 6.5 Rutinas
```
GET /api/routines
  200: {
    "lunes": {"day_key","name","focus","sort",
      "blocks":[{"id","title","sort",
        "items":[{"id","name","pattern_id","variant_a","variant_b","variant_c","sort"}]}]},
    ... (martes..viernes)
  }
  # Estructura completa anidada y ordenada por sort en cada nivel.

GET /api/routines/{day_key}
  200: el objeto del día (misma forma que arriba para una clave).

GET /api/routines/{day_key}/for-athlete/{athlete_id}
  200: {"day_key","name","focus",
        "blocks":[{"title","items":[{"name","pattern_id","level":"B","text":"<variante resuelta>"}]}]}
  # Server resuelve la variante por alumno (algoritmo §1.3). Conveniencia para la vista "Por alumno".

# --- Edición ---
PATCH /api/routines/{day_key}
  body: {"focus"?: str, "name"?: str}
  200: día actualizado.

POST /api/routines/{day_key}/blocks
  body: {"title": str}
  201: bloque creado (sort = max+1).

PATCH /api/routines/blocks/{block_id}
  body: {"title"?: str, "sort"?: int}
DELETE /api/routines/blocks/{block_id}   → cascade borra ejercicios.

POST /api/routines/blocks/{block_id}/exercises
  body: {"name": str, "pattern_id": str, "variant_a":"", "variant_b":"", "variant_c":""}
  201: ejercicio creado (sort = max+1).

PATCH /api/routines/exercises/{exercise_id}
  body parcial: {"name"?,"pattern_id"?,"variant_a"?,"variant_b"?,"variant_c"?,"sort"?}
DELETE /api/routines/exercises/{exercise_id}

# Reordenamiento (opcional v1, recomendado):
PUT /api/routines/blocks/{block_id}/reorder
  body: {"exercise_ids": [id, id, ...]}   # nuevo orden → reescribe sort 0..n
```

### 6.6 Pruebas (definición de batería)
```
GET /api/tests?include_archived=false
  200: [{"id","name","pattern_id","unit","better","sort","archived"}, ...]

POST /api/tests
  body: {"name","pattern_id","unit","better"}
  201: prueba creada (id = slug generado a partir del nombre + sufijo si colisiona; sort=max+1).

PATCH /api/tests/{id}
  body parcial: {"name"?,"pattern_id"?,"unit"?,"better"?,"sort"?,"archived"?}

DELETE /api/tests/{id}
  200: {"ok": true}   # SOFT delete (archived=1) si tiene mediciones; físico si no tiene ninguna.
```

### 6.7 Sesiones de prueba y mediciones
```
GET /api/sessions
  200: [{"id","date","note","created_at"}, ...]   # orden por date asc.

GET /api/sessions/latest
  200: la sesión más reciente con sus mediciones (para "comparar con la anterior") o null.

GET /api/sessions/{id}
  200: {"id","date","note",
        "measurements":[{"athlete_id","test_id","raw_value"}, ...]}

POST /api/sessions
  body: {
    "date": <epoch ms>,
    "note": "",
    "measurements": [{"athlete_id": int, "test_id": str, "raw_value": str}, ...]
  }
  201: sesión creada con sus mediciones (transacción única).
  # Reglas: ignora mediciones con raw_value vacío. Si (athlete,test) repetido en payload, último gana.

PATCH /api/sessions/{id}
  body: {"date"?, "note"?, "measurements"?}   # measurements reemplaza el set completo de la sesión.

DELETE /api/sessions/{id}   → cascade borra mediciones.
```

### 6.8 Progreso (series temporales)
```
GET /api/progress?athlete_id={id}&test_id={tid}
  200: {
    "test": {"id","name","unit","better"},
    "points": [{"date": <ms>, "raw":"12", "num": 12.0}, ...]   # orden por date asc, solo no vacíos
  }
  # 'num' = raw convertido según unit (mm:ss→segundos). El front grafica 'num' y muestra 'raw'.
```

### 6.9 Exportación / compartir
```
GET /api/export/session/{id}.txt
  200 text/plain:  resumen legible (ver formato en §6.10) — para copiar/compartir por WhatsApp.

GET /api/export/session/{id}.csv
  200 text/csv:    columnas: alumno, prueba, unidad, valor.

GET /api/export/backup.json     (opcional, recomendado)
  200 application/json: volcado completo (alumnos, niveles, rutinas, tests, sesiones) para respaldo.

POST /api/import/backup.json    (opcional)
  body: el JSON de backup → restaura (con confirmación en UI). Útil para migrar de VM.
```

### 6.10 Lógica de negocio (server/logic.py)

**Parseo de valor → número comparable:**
```python
def to_num(unit: str, raw: str) -> float | None:
    if raw is None or raw.strip() == "":
        return None
    raw = raw.strip()
    if unit == "mm:ss":
        if ":" in raw:
            m, s = raw.split(":", 1)
            return int(m) * 60 + float(s)
        return float(raw)               # admite segundos sueltos
    return float(raw.replace(",", "."))
```

**Delta y si es mejora:**
```python
def delta(better: str, unit: str, cur_raw: str, prev_raw: str):
    cur, prev = to_num(unit, cur_raw), to_num(unit, prev_raw)
    if cur is None or prev is None:
        return None
    d = cur - prev
    if d == 0:
        return {"value": 0, "improved": None}
    improved = (d > 0) if better == "high" else (d < 0)
    return {"value": d, "improved": improved}
```

**Resolución de variante por alumno (algoritmo nuclear §1.3):**
```python
def resolve_variant(exercise, level: str) -> str:
    return {"A": exercise.variant_a,
            "B": exercise.variant_b,
            "C": exercise.variant_c}.get(level, exercise.variant_a)
```

**Formato de resumen de texto (export .txt):**
```
MÉTODO FUNCIONAL — Resultados <DD mmm YYYY>

<Nombre alumno>
  · <Prueba>: <valor formateado>
  · ...

<Siguiente alumno>
  ...
```
Reglas de formato: para `reps` mostrar solo el número; para `seg`/`cm`/`kg`/`m` añadir la unidad; para `mm:ss` mostrar el texto tal cual. Omitir alumnos sin ninguna medición en esa sesión.
-e 

---

# Parte 3 — Frontend: vistas, comportamiento y diseño

## 7. Frontend (React + Vite)

### 7.1 Principios
- SPA con React 18. Routing con `react-router-dom` (rutas: `/login`, `/`, `/prueba`, `/progreso`, `/alumnos`, `/editar`).
- Estado global ligero con Context + hooks (`state/store.jsx`): cachea patrones, alumnos, rutinas, tests y sesiones tras login; expone acciones que llaman a la API y refrescan.
- Wrapper `api.js`: `fetch` con `credentials: "include"`; si recibe 401 → redirige a `/login`.
- Mobile-first: la app se usa en el parque desde el móvil. Todo debe funcionar a 360px de ancho y con una mano.
- Sin librerías de UI pesadas. Gráfica con SVG propio (no Recharts) para mantener el bundle pequeño; el prototipo ya tiene una implementación válida que puede portarse.

### 7.2 Guía de diseño visual (tomada del prototipo aprobado)
El prototipo HTML ya validado define la identidad; respetarla.

**Paleta (CSS vars):**
```
--bg:#14181c  --bg2:#1b2025  --card:#1f262c  --card2:#262e35  --line:#323b43
--ink:#eef2f4  --ink-dim:#9aa6ad  --ink-faint:#69757c
--brick:#d8472b   (rojo tartán de pista — acento de marca)
--lvlA:#d8472b  --lvlB:#e6a02c  --lvlC:#3fae7a   (códigos de nivel A/B/C)
--up:#3fae7a  --down:#e8654f
```
- Tema oscuro tipo "pizarra de entrenador". Acento rojo ladrillo.
- **Código de color de niveles consistente en TODA la app:** A=rojo, B=ámbar, C=verde. Nunca cambiar este mapeo.
- Tipografía: una fuente condensada para títulos/etiquetas (estética dorsal/cronómetro) y una sans neutra para cuerpo. El prototipo usa Arial Narrow + Helvetica/Arial como fallback; el agente puede sustituir por fuentes web equivalentes (p. ej. "Oswald"/"Barlow Condensed" para títulos, "Inter" para cuerpo) si las empaqueta localmente (sin CDN en producción).
- Bordes redondeados suaves (7–12px), líneas finas `--line`, sombras mínimas.
- Elemento de firma: el "tablero del día" (board) con eyebrow rojo, nombre del día en condensada grande y etiqueta HOY.

### 7.3 Navegación
Barra de pestañas fija (sticky top tras el header): **Hoy · Prueba · Progreso · Alumnos · Editar**. En móvil puede ir como barra inferior si se prefiere; mantener orden y etiquetas.

### 7.4 Vista LOGIN (`/login`)
- Card centrada: logo/marca, campo email, campo password, botón "Entrar".
- Error inline bajo el botón si credenciales inválidas (mensaje del backend).
- Tras éxito → redirige a `/`. Si ya hay sesión (`/api/auth/me` 200) y el usuario entra a `/login`, redirige a `/`.

### 7.5 Vista HOY (`/`)
- Selector de día (lun–vie) como botones; marca el día actual automáticamente al entrar (mapear `Date.getDay()` → day_key; sábado/domingo cae en 'lunes' por defecto, indicándolo sutilmente).
- "Board" del día: eyebrow "Sesión del día", nombre del día, focus, etiqueta HOY si aplica.
- Selector "Ver para": `Todos (A/B/C)` o un alumno concreto (lista de no archivados).
  - **Modo Todos:** cada ejercicio muestra las 3 variantes apiladas, cada una con su tag de color (A/B/C) y texto.
  - **Modo Por alumno:** cada ejercicio muestra UNA línea: tag grande con el nivel del alumno en el patrón del ejercicio (color correspondiente) + el texto de esa variante. Usar preferentemente `GET /routines/{day}/for-athlete/{id}` para que el server resuelva, o resolver en cliente con los datos ya cargados (ambas válidas; si se resuelve en cliente, replicar exactamente el algoritmo §1.3).
- Bloques con su título; ejercicios en orden.

### 7.6 Vista PRUEBA (`/prueba`)
Flujo de captura en día de evaluación:
- Campo **fecha** (default hoy). Indicador "Comparando con <fecha de la última sesión guardada>".
- Selector de **prueba activa** (chips horizontales, una prueba a la vez para captura cómoda en móvil).
- Tarjeta de la prueba activa: nombre, unidad, y nota de dirección ("más es mejor" / "menos es mejor").
- Lista de alumnos (no archivados). Por alumno una fila:
  - tag de nivel (color) del patrón de esa prueba,
  - nombre,
  - **input** de valor (numérico; para `mm:ss` placeholder "mm:ss"),
  - valor previo ("antes 12") si existe en la última sesión,
  - **delta** coloreado (verde/rojo según `improved`) calculado al vuelo.
- Estado local acumula valores de TODAS las pruebas mientras el usuario cambia de chip (no se pierde lo capturado al cambiar de prueba).
- Acciones:
  - **Guardar prueba** → `POST /api/sessions` con todas las mediciones no vacías. Toast "Prueba guardada ✓". Limpia el formulario.
  - **Compartir resumen** → obtiene `/api/export/session/{id}.txt` (de la recién guardada) o genera el texto en cliente; usa `navigator.share()` si existe, si no copia al portapapeles con toast "Resumen copiado ✓".
- Validación: si no hay ninguna medición, toast "Anota al menos un resultado" y no guarda.

### 7.7 Vista PROGRESO (`/progreso`)
- Selectores: **alumno** y **prueba**.
- **Gráfica** SVG de línea: eje X = fechas de sesiones, eje Y = valor (`num`). Punto por sesión, línea entre puntos. Etiqueta de tendencia (▲ mejora / ▼ baja) comparando primer vs. último punto según `better`. Para pruebas `better=low` mostrar nota "menos es mejor (tiempo)".
- **Historial**: lista descendente (más reciente primero) de fecha + valor formateado + delta vs. sesión previa (coloreado).
- Estado vacío: si no hay sesiones, mensaje "Aún no hay pruebas guardadas" con CTA hacia Prueba.

### 7.8 Vista ALUMNOS (`/alumnos`)
- Intro breve recordando que los niveles son por patrón y pueden mezclarse.
- Tarjeta por alumno:
  - input de nombre (guarda on blur / debounce → `PATCH /athletes/{id}`),
  - botón archivar (×) con confirmación,
  - **grid de 5 patrones**; por patrón, tres botones A/B/C; el activo se pinta con el color del nivel. Tap → `PUT /athletes/{id}/levels`.
- Botón "+ Añadir alumno" → `POST /athletes` (crea con niveles 'A'). Límite suave 12 (mensaje si se excede).

### 7.9 Vista EDITAR (`/editar`)
Dos subpestañas: **Rutinas** y **Pruebas**.
- **Rutinas:** selector de día; editar `focus`; por bloque: título editable, borrar bloque, lista de ejercicios; por ejercicio: nombre, selector de patrón, tres inputs de variante (A/B/C con su color), borrar; "+ Ejercicio"; "+ Añadir bloque". Reordenar es deseable (drag o flechas) pero opcional en v1.
- **Pruebas:** lista editable: nombre, selector de patrón, selector de unidad, selector de dirección (más/menos mejor), borrar; "+ Añadir prueba".
- Todas las ediciones persisten contra la API correspondiente. Mostrar toasts de confirmación discretos o guardado optimista con reconciliación.

### 7.10 Componentes reutilizables
- `LevelTag({level, size})`: cuadro con letra A/B/C y color del nivel.
- `ExerciseRow`: soporta modo "all" y modo "solo" (un nivel).
- `Chart({points, test})`: SVG responsive (portar del prototipo).
- `Toast`, `ConfirmDialog`, `DayBar`, `TabBar`, `Field`.

### 7.11 Estados de carga, error y vacío
- Spinner/placeholder mientras carga el estado inicial tras login.
- Errores de red → toast "No se pudo conectar. Reintenta." y permitir reintento; no perder datos capturados.
- Empties con dirección (qué hacer), nunca pantallas en blanco.

### 7.12 Accesibilidad y calidad de base
- Focus visible en todos los controles; targets táctiles ≥ 40px.
- Contraste suficiente (texto sobre fondos oscuros).
- `prefers-reduced-motion` respetado (desactiva animaciones de entrada).
- Funciona sin conexión tras carga si se implementa PWA (§8); sin PWA, requiere red para la API.
-e 

---

# Parte 4 — Datos semilla, despliegue, seguridad, pruebas y entrega

## 8. Datos semilla (server/seed.py)

El seed debe ser **idempotente** (si ya hay datos, no duplica). Crea: usuario admin, patrones, rutinas completas, batería de pruebas y 5 alumnos de ejemplo.

### 8.1 Usuario admin
Lee `ADMIN_EMAIL` y `ADMIN_PASSWORD` del entorno. Si no existe un usuario con ese email, lo crea con hash bcrypt. Si ya existe, no lo toca.

### 8.2 Patrones
```
empuje/Empuje/1, traccion/Tracción/2, pierna/Pierna/3, carrera/Carrera/4, core/Core/5
```

### 8.3 Rutinas (datos completos a insertar)

> Formato por ejercicio: `name | pattern | A | B | C`. Mantener este contenido exacto como semilla; es editable después desde la app.

**LUNES — "Empuje + Core"**
- Bloque "Bloque principal · 3 rondas":
  - Flexiones | empuje | Inclinadas en barra · 8–10 | Estándar al suelo · 8–12 | Diamante / pseudo-planche · 10–12
  - Fondos | empuje | Banco, pies apoyados · 6–8 | En paralelas · 6–10 | Lastrados o tempo 3·1 · 8–10
  - Empuje vertical | empuje | Pike manos altas · 6–8 | Pike al suelo · 8–10 | Pike elevado / a vertical · 6–8
  - Core anti-extensión | core | Plancha 20–30 s | Hollow 30–40 s | Hollow + balanceo 40 s
- Bloque "Cierre · 5 min":
  - Trote suave + estiramiento | empuje | 2×100 m + pectoral/hombro | 2×100 m + pectoral/hombro | 2×100 m + pectoral/hombro

**MARTES — "Carrera / Capacidad aeróbica"**
- Bloque "Calentamiento":
  - Activación | carrera | Trote 5 min + movilidad | Trote 6 min + 3 progresivos | Trote 6 min + 4 progresivos
- Bloque "Bloque de series · por tiempo":
  - Intervalos | carrera | 4×(2 min fuerte / 2 min suave) | 5×(2 min fuerte / 90 s suave) | 6×(2 min fuerte / 75 s suave)
- Bloque "Vuelta a la calma":
  - Regenerativo | carrera | Caminata 3 min + respiración | Trote 4 min | Trote 5 min

**MIÉRCOLES — "Tracción + Core"**
- Bloque "Bloque principal · 3 rondas":
  - Dominada | traccion | Remo australiano · 8–10 | Asistida / negativas · 4–6 | Estricta · 6–10
  - Remo horizontal | traccion | Invertido pies al suelo · 8–10 | Invertido pies elevados · 8–12 | A una mano / archer · 6–8
  - Agarre / colgado | traccion | Colgado pasivo 15–20 s | Colgado activo 20–30 s | Colgado + rodillas · 8–10
  - Core anti-rotación | core | Plancha lateral 15–20 s | Plancha lateral 25–35 s | Lateral + elevación cadera · 8
- Bloque "Cierre · 5 min":
  - Movilidad hombro | traccion | Banda + dorsal/antebrazo | Banda + dorsal/antebrazo | Banda + dorsal/antebrazo

**JUEVES — "Tren inferior + Potencia"**
- Bloque "Parte A · Fuerza · 3 rondas":
  - Sentadilla | pierna | A banco / cajón · 10–12 | Libre profunda · 12–15 | Búlgara · 8–10/pierna
  - Unilateral | pierna | Zancada estática asist. · 8 | Zancada caminando · 10 | Pistol asistido · 5–8
  - Cadena posterior | pierna | Puente 2 piernas · 12–15 | Puente 1 pierna · 8–10 | Curl nórdico asist. · 5–8
- Bloque "Parte B · Potencia":
  - Salto | pierna | Cajón bajo · 5×3 | Vertical máximo · 5×3 | Drop jump · 5×3
  - Aceleración | carrera | Sprint 20 m · 4 | Sprint 30 m · 5 | Sprint 40 m dinám. · 6

**VIERNES — "Mixto / Game Day"**
- Bloque "AMRAP 20 min · 5 estaciones":
  - 1 · Empuje | empuje | Flexiones · 8 | Flexiones · 12 | Diamante · 12
  - 2 · Tracción | traccion | Remo australiano · 8 | Dominada asist. · 5 | Dominada estricta · 8
  - 3 · Pierna | pierna | Sentadilla · 12 | Zancada · 10/p | Búlgara · 8/p
  - 4 · Carrera | carrera | Sprint 50 m | Sprint 80 m | Sprint 100 m
  - 5 · Core | core | Plancha 30 s | Hollow 40 s | Colgado + rodillas · 10

### 8.4 Batería de pruebas (semilla)
```
flex    | Flexiones máximas     | empuje   | reps  | high
dom     | Dominadas / remos máx.| traccion | reps  | high
v700    | Vuelta 700 m          | carrera  | mm:ss | low
salto   | Salto vertical        | pierna   | cm    | high
plancha | Plancha / hollow máx. | core     | seg   | high
```

### 8.5 Alumnos de ejemplo (semilla; renombrables)
```
Alumno 1 | empuje:B traccion:A pierna:B carrera:B core:A
Alumno 2 | empuje:A traccion:A pierna:A carrera:A core:A
Alumno 3 | empuje:C traccion:B pierna:C carrera:B core:B
Alumno 4 | empuje:B traccion:C pierna:A carrera:C core:B
Yo       | empuje:C traccion:C pierna:C carrera:C core:C
```

---

## 9. Configuración y variables de entorno

`.env.example`:
```
# App
APP_ENV=production
HOST=127.0.0.1
PORT=8080
DB_PATH=./data/app.db
SESSION_SECRET=__genera_uno_largo_aleatorio__     # 64+ chars; openssl rand -hex 32
COOKIE_SECURE=true                                # true en producción (HTTPS)

# Usuario admin inicial (solo se usa en el seed)
ADMIN_EMAIL=tu-correo@ejemplo.com
ADMIN_PASSWORD=__cámbiala__
```

`server/config.py` con `pydantic-settings` lee estas variables. `COOKIE_SECURE=false` solo para desarrollo local sin HTTPS.

Dependencias backend (`pyproject.toml` o `requirements.txt`):
```
fastapi
uvicorn[standard]
sqlmodel
passlib[bcrypt]
pydantic-settings
itsdangerous            # firma de SessionMiddleware
python-multipart        # forms si se usan
```

---

## 10. Seguridad

- **Sesión:** cookie httpOnly + Secure + SameSite=Lax, firmada con `SESSION_SECRET`. Sin secret no arranca.
- **Hashing:** bcrypt vía passlib. Nunca guardar contraseñas en claro ni en logs.
- **Sin registro público:** el alta de usuario solo por seed. No exponer endpoint de signup.
- **CORS:** innecesario (single origin). No habilitar CORS abierto.
- **Rate limit de login:** limitar intentos (p. ej. 5/min por IP) con un middleware simple en memoria; opcional pero recomendado al estar expuesto a internet.
- **nginx** termina TLS con Let's Encrypt (certbot); HTTP→HTTPS forzado. FastAPI escucha solo en `127.0.0.1:8091` (no expuesto directo). Cloudflare en nube gris solo resuelve DNS.
- **Cabeceras:** nginx añade HSTS y `nosniff`/`X-Frame-Options`; FastAPI también devuelve `X-Content-Type-Options: nosniff` y `X-Frame-Options: DENY`. CSP básica recomendada para la SPA (sin inline scripts externos).
- **Backups:** el endpoint `/api/export/backup.json` + copia periódica del archivo `app.db` (cron). Documentarlo en README-deploy.
- **Validación estricta** de `pattern_id`, `level`, `unit`, `better` contra catálogos antes de escribir.

---

## 11. Despliegue en la VM (Ubuntu) — nginx + Cloudflare nube gris

Guía completa y reproducible en [`deploy/README-deploy.md`](deploy/README-deploy.md). Resumen:

### 11.1 Build del frontend
```
cd client && npm ci && npm run build      # genera client/dist
```
FastAPI monta `client/dist` como estáticos y hace fallback de SPA a `index.html` para rutas no-`/api`. nginx **no** sirve estáticos: solo reverse-proxya a Uvicorn (ADR-2/ADR-8).

### 11.2 Backend
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # editar valores reales (SESSION_SECRET, ADMIN_*, COOKIE_SECURE=true, PORT=8091)
python -m server.seed  # crea admin + semilla (idempotente)
# Verificar que el puerto está libre: ss -ltnp | grep ':8091'
```

### 11.3 systemd (`deploy/tablero-entrenador.service`)
```ini
[Unit]
Description=Tablero del Entrenador (FastAPI/Uvicorn)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/tablero_entrenador
EnvironmentFile=/home/ubuntu/tablero_entrenador/.env
ExecStart=/home/ubuntu/tablero_entrenador/.venv/bin/uvicorn server.main:app \
    --host 127.0.0.1 --port 8091 \
    --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```
```
sudo systemctl enable --now tablero-entrenador
```
`--proxy-headers` es necesario porque nginx termina TLS y proxya HTTP (ADR-10): así FastAPI ve el esquema https y la cookie `Secure` funciona.

### 11.4 nginx (`deploy/nginx/fitness.streamlytics.stream.conf`)
```
sudo cp deploy/nginx/fitness.streamlytics.stream.conf /etc/nginx/sites-available/fitness.streamlytics.stream
sudo ln -s /etc/nginx/sites-available/fitness.streamlytics.stream /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```
El vhost hace `proxy_pass http://127.0.0.1:8091` y reenvía `X-Forwarded-Proto $scheme`, con HSTS, gzip y `client_max_body_size` para los backups.

### 11.5 TLS con Let's Encrypt (certbot)
```
sudo certbot --nginx -d fitness.streamlytics.stream
sudo nginx -t && sudo systemctl reload nginx
```
En **nube gris (DNS only)** el challenge HTTP-01 llega directo al origen, así que certbot emite y renueva el certificado sin configuración extra. (Alternativa DNS-01 con token de Cloudflare si algún día se usa nube naranja; no necesario aquí.)

### 11.6 Notas de Cloudflare nube gris
- El registro **A** de `fitness.streamlytics.stream` apunta a la IP pública de la VM y está en **DNS only** (icono gris): el tráfico no pasa por el proxy de Cloudflare.
- Los puertos 80/443 ya están abiertos en la VM (la hospeda junto a otros proyectos); no hace falta tocar firewall.
- El certificado lo emite **Let's Encrypt**, no Cloudflare. Verificar con `openssl s_client ... | openssl x509 -noout -issuer`.

---

## 12. Criterios de aceptación (definición de "hecho")

El agente debe entregar una app que cumpla, verificable manualmente:

1. **Login:** con las credenciales del seed entro; con credenciales falsas obtengo error claro; sin sesión, cualquier `/api/*` protegido responde 401 y la SPA me manda a `/login`.
2. **Hoy/Todos:** al abrir, se preselecciona el día actual y veo cada ejercicio con sus 3 variantes A/B/C coloreadas.
3. **Hoy/Por alumno:** al elegir un alumno, cada ejercicio muestra solo su variante según el nivel del alumno en el patrón de ese ejercicio. Verificable con un alumno de niveles mixtos (p. ej. C en pierna, A en tracción): el jueves muestra variantes C en ejercicios de pierna y el miércoles variantes A en tracción.
4. **Alumnos:** puedo crear, renombrar, archivar y cambiar niveles por patrón; el cambio se refleja inmediatamente en la vista Hoy/Por alumno.
5. **Prueba:** elijo fecha, capturo valores por alumno en varias pruebas cambiando de chip sin perder lo anotado, veo el delta vs. la última sesión, guardo, y la sesión queda persistida.
6. **Compartir:** obtengo un resumen de texto con formato §6.10 y puedo copiarlo/compartirlo.
7. **Progreso:** tras ≥2 sesiones, la gráfica muestra la evolución por alumno+prueba, con tendencia correcta según `better` (en v700, bajar el tiempo se marca como mejora).
8. **Editar:** modifico una variante de un ejercicio y un nombre de prueba; persiste y se ve reflejado en Hoy y Prueba.
9. **Persistencia multi-dispositivo:** lo guardado desde el móvil aparece al entrar desde la laptop (misma cuenta, mismo servidor).
10. **Deploy:** corre como servicio systemd detrás de Caddy con HTTPS, sobrevive a reinicio de la VM.

---

## 13. Pruebas automatizadas mínimas (recomendado)

- **Backend (pytest + httpx):**
  - `to_num` y `delta` (incluye mm:ss y dirección `low`).
  - Resolución de variante por nivel.
  - Auth: login ok/fallo, acceso protegido sin sesión = 401.
  - CRUD de alumnos + `PUT levels` valida nivel/patrón.
  - `POST /sessions` ignora vacíos y deduplica (athlete,test).
  - `GET /progress` ordena por fecha y convierte `num`.
- **Frontend (opcional, Vitest + Testing Library):** render de ExerciseRow en ambos modos; cálculo de delta en la vista Prueba.

---

## 14. Roadmap posterior a v1 (no implementar ahora, dejar preparado)

- Indicador de semana del bloque de 4 semanas (carga/descarga) y banner de "semana de descarga".
- Reordenamiento drag-and-drop de bloques/ejercicios.
- PWA: manifest + service worker para uso offline en el parque (cachear shell + último estado; cola de escritura para sincronizar al recuperar red).
- Exportar/Importar backup completo desde la UI (endpoints ya descritos en §6.9).
- Histórico de cambios de nivel por alumno (auditoría de progreso de niveles, no solo de pruebas).
- Multi-grupo (si algún día entrena a más de un grupo).

---

## 15. Preguntas abiertas para el dueño (resolver antes o durante implementación)

Ninguna es bloqueante; defaults propuestos entre paréntesis:

1. **Dominio:** ✅ **Resuelto.** Subdominio `fitness.streamlytics.stream` apuntando a la VM vía Cloudflare en **nube gris (DNS only)**; TLS por Let's Encrypt en nginx (ver §11 y ADR-6).
2. **Días de entrenamiento:** la rutina semilla cubre lunes–viernes. ¿Quieres dejar habilitado sábado para sesiones extra o mantener solo 5 días? (Default: 5 días.)
3. **Unidades:** ¿la vuelta de 700 m la mides siempre en mm:ss, o a veces en segundos planos? (Default: mm:ss, el parser acepta ambos.)
4. **Backups:** ¿quieres un cron de respaldo automático del `app.db` a otra ubicación/Object Storage de Oracle? (Default: cron local diario + retención 14 días, documentado.)
5. **Fuentes:** ¿OK con empaquetar fuentes web libres (Oswald/Barlow + Inter) localmente, o prefieres fuentes del sistema? (Default: empaquetar libres, sin CDN.)
6. **Idioma:** todo en español. ¿Algún término que prefieras distinto (p. ej. "alumnos" vs "atletas")? (Default: "alumnos".)

---

## 16. Iteración 2 — Medios, CSV, PWA y UI móvil (implementado)

Ampliación posterior a v1, ya implementada. Decisiones detalladas (ADR-11 a ADR-15) en
[`docs/PLAN-Y-DECISIONES.md`](docs/PLAN-Y-DECISIONES.md); checklist en [`docs/PRUEBAS.md`](docs/PRUEBAS.md).

### 16.1 Medios por variante
- `routine_exercises` añade `media_a/b/c` (migración aditiva idempotente en `db.py`).
- **Subida** de imagen/gif: `POST /api/uploads` (multipart, ≤ 5 MB, JPG/PNG/GIF/WebP) → guarda en
  `data/uploads/` y devuelve `{"url":"/media/<x>"}`. Servido en `/media` (StaticFiles). **Video** por URL.
- La API de rutinas propaga `media_a/b/c`; `for-athlete` añade `media` resuelto al nivel del alumno.
- **Frontend:** ruta `/ejercicio/:dayKey/:exerciseId` (visor a pantalla completa con `MediaView`:
  imagen/gif, embed YouTube/Vimeo o `<video>`), botón "Mostrar ejercicio" en Hoy, navegación prev/next.

### 16.2 Import/Export CSV (rutinas y pruebas)
- `GET /api/export/{routines,tests}.csv` (con BOM UTF-8 para Excel) y
  `POST /api/import/{routines,tests}.csv` (multipart, **reemplazar todo**, tolera `,`/`;`).
- Rutinas: borrado total + recreación. Pruebas: upsert por id + archivar/borrar ausentes (preserva
  mediciones). Esquemas de columnas documentados en `server/routers/csvio.py`. UI en Editar (componente `CsvBar`).

### 16.3 PWA instalable
- `vite-plugin-pwa` (Workbox): manifest + service worker (shell precacheado, API `NetworkOnly`,
  medios `CacheFirst`). Logo **pesa + figura corriendo** (`client/public/icons/logo.svg`) rasterizado a
  PNG con `npm run icons` (sharp). Meta `apple-touch-icon`/`apple-mobile-web-app-*` en `index.html`.

### 16.4 UI móvil
- Barra de navegación **inferior fija** con iconos, áreas táctiles ≥ 44 px y `env(safe-area-inset-*)`;
  inputs a 16 px (evita zoom iOS). Refinamiento de board, cards, chips y formularios.

### 16.5 Archivos nuevos (iteración 2)
```
server/routers/uploads.py        # subida de imágenes/gifs
server/routers/csvio.py          # import/export CSV
client/src/pages/ExerciseView.jsx
client/src/components/{MediaView,MediaPicker,CsvBar}.jsx
client/src/lib/media.js
client/public/icons/              # logo.svg + PNGs (192/512/maskable/apple-touch/favicon)
client/scripts/gen-icons.mjs      # genera los PNG con sharp
```
