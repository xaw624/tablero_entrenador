# Guía de pruebas y verificación

Cómo probar el Tablero del Entrenador en local, correr la suite automatizada y verificar
manualmente los criterios de aceptación (§12 de la especificación).

---

## 1. Correr en local (desarrollo)

Backend (con HTTP, sin TLS → `COOKIE_SECURE=false`):

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows ; en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env             # edita SESSION_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD, COOKIE_SECURE=false
python -m server.seed
```

Dos modos de frontend:

- **Build servido por FastAPI (igual que producción):**
  ```bash
  cd client && npm install && npm run build && cd ..
  .venv\Scripts\python -m uvicorn server.main:app --port 8091 --reload
  # http://127.0.0.1:8091
  ```
- **Hot-reload de Vite (desarrollo de UI):**
  ```bash
  # terminal 1: backend
  uvicorn server.main:app --port 8091 --reload
  # terminal 2: frontend con proxy /api → :8091
  cd client && npm run dev      # http://127.0.0.1:5173
  ```

Credenciales de entrada: las de `ADMIN_EMAIL` / `ADMIN_PASSWORD` del `.env`.

> Nota Windows: si la consola corta por acentos al ejecutar el seed, usa `set PYTHONUTF8=1`
> (cmd) o `$env:PYTHONUTF8="1"` (PowerShell) antes del comando.

---

## 2. Suite automatizada (pytest)

```bash
pytest
```

Cubre (§13):

| Archivo | Qué valida |
|---|---|
| `tests/test_logic.py` | `to_num` (incl. `mm:ss`), `delta` (dirección `low`), `resolve_variant`, `format_value` |
| `tests/test_auth.py` | login ok/fallo, acceso protegido sin sesión = 401, logout |
| `tests/test_athletes.py` | niveles sembrados, alta con niveles 'A', `PUT levels`, validación, soft delete |
| `tests/test_sessions_progress.py` | `POST /sessions` ignora vacíos y deduplica; `progress` ordena por fecha y convierte `num` |

La suite usa una base aislada (`data/_pytest.db`) que se recrea en cada corrida; no toca `app.db`.

---

## 3. Checklist manual (criterios de aceptación §12)

Marca cada punto entrando como el entrenador. Datos semilla cargados.

- [ ] **1 · Login.** Con las credenciales del seed entro. Con credenciales falsas veo
  "Credenciales inválidas". Sin sesión, cualquier `/api/*` protegido responde 401 y la SPA
  me manda a `/login`.
- [ ] **2 · Hoy / Todos.** Al abrir, se preselecciona el día actual (fin de semana → lunes,
  indicado). Cada ejercicio muestra las 3 variantes A/B/C con sus colores (A rojo, B ámbar, C verde).
- [ ] **3 · Hoy / Por alumno (caso nuclear).** Elijo **Alumno 3** (C en pierna, B en tracción):
  - En **Jueves** (tren inferior) los ejercicios de patrón *pierna* muestran la variante **C**
    (p. ej. Sentadilla → "Búlgara · 8–10/pierna").
  - En **Miércoles** (tracción) los ejercicios de *traccion* muestran la variante **B**.
- [ ] **4 · Alumnos.** Creo, renombro (on blur), archivo (con confirmación) y cambio niveles
  por patrón (tap A/B/C). El cambio se refleja al instante en Hoy / Por alumno.
- [ ] **5 · Prueba.** Elijo fecha; capturo valores por alumno cambiando de chip de prueba
  **sin perder** lo anotado; veo "antes X" y el delta coloreado vs. la última sesión; guardo
  ("Prueba guardada ✓") y la sesión queda persistida.
- [ ] **6 · Compartir.** Tras guardar, "Compartir resumen" usa `navigator.share` o copia al
  portapapeles ("Resumen copiado ✓") el texto con formato §6.10.
- [ ] **7 · Progreso.** Con ≥2 sesiones, la gráfica muestra la evolución por alumno+prueba.
  En **v700** (`better=low`) bajar el tiempo se marca como mejora (▲) y aparece "menos es mejor (tiempo)".
- [ ] **8 · Editar.** Modifico una variante de un ejercicio y un nombre de prueba; persiste y
  se ve reflejado en Hoy y Prueba.
- [ ] **9 · Persistencia multi-dispositivo.** Lo guardado desde el móvil aparece al entrar
  desde la laptop (misma cuenta, mismo servidor).
- [ ] **10 · Deploy.** Corre como servicio systemd detrás de nginx con HTTPS (Let's Encrypt),
  y sobrevive a reinicio de la VM (`systemctl is-enabled tablero-entrenador`).

---

## 4. Verificación rápida por API (smoke con curl)

```bash
BASE=http://127.0.0.1:8091          # o https://fitness.streamlytics.stream
curl -s $BASE/api/health            # {"status":"ok"}
# login guardando cookie
curl -s -c cookies.txt -X POST $BASE/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"TU_EMAIL","password":"TU_PASS"}'
curl -s -b cookies.txt $BASE/api/athletes | head -c 200
# caso nuclear: jueves de Alumno 3 (sustituye 3 por su id real)
curl -s -b cookies.txt "$BASE/api/routines/jueves/for-athlete/3"
```

---

## 4b. Funciones de la iteración 2 (medios, CSV, PWA)

### Medios por variante + visor
- [ ] En **Editar → Rutinas**, en un ejercicio, cada variante A/B/C tiene un campo de **Medio**:
  pego una URL de YouTube o **subo** una imagen/gif (botón "Subir"). Se guarda al instante.
- [ ] En **Hoy**, el ejercicio muestra **"▶ Mostrar ejercicio"**; al pulsar abre la página completa
  `/ejercicio/...` con el medio grande, el nombre y selector A/B/C.
- [ ] **Anterior/Siguiente** recorre los ejercicios del día; **Volver** regresa a Hoy.
- [ ] En modo **Por alumno**, el visor abre en el nivel del alumno (badge "· su nivel").
- [ ] Tipos de medio: imagen/gif → se ve la imagen; YouTube/Vimeo → reproductor embebido;
  `.mp4` → `<video>`; otro enlace → botón "Abrir video ↗".

### Import / Export CSV
- [ ] En **Editar → Rutinas** y **→ Pruebas**, la barra superior permite **Exportar CSV** (descarga).
- [ ] Abro el CSV en Excel (acentos correctos por BOM), edito y guardo como CSV.
- [ ] **Importar CSV** pide confirmación ("reemplazará…") y al aceptar reemplaza el contenido;
  un CSV con `pattern_id`/`unit`/`better` inválido se rechaza con mensaje claro.
- [ ] Excel con `;` como separador también se importa (se autodetecta).

### PWA (instalable)
- [ ] En Chrome (escritorio) aparece "Instalar app"; en Android/iOS, "Añadir a pantalla de inicio"
  muestra el **logo (pesa + figura corriendo)**.
- [ ] Abierta desde el icono, corre en modo **standalone** (sin barra del navegador).
- [ ] Tras una primera carga con red, el **shell** abre aunque la red falle (la API sí requiere red).

Verificación rápida con curl (build servido por FastAPI):
```bash
curl -sI $BASE/manifest.webmanifest | grep -i content-type   # application/manifest+json
curl -sI $BASE/sw.js | head -1                                # 200
curl -sI $BASE/icons/icon-192.png | grep -i content-type      # image/png
```

## 5. Móvil (mobile-first)

Probar a **360 px** de ancho (DevTools → responsive). Verificar que:
- Todo es operable con una mano; targets táctiles ≥ 40 px.
- Los chips de día/prueba y los inputs de captura no se cortan.
- `prefers-reduced-motion` desactiva animaciones (no hay parpadeos).
