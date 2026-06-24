# Plan y decisiones de implementación

Registro del plan seguido y de las decisiones de arquitectura tomadas al construir el
Tablero del Entrenador, con foco en el cambio de despliegue solicitado (Caddy → nginx +
Cloudflare nube gris). Complementa la especificación funcional
[`../ESPECIFICACION_Tablero_Entrenador.md`](../ESPECIFICACION_Tablero_Entrenador.md).

---

## 1. Contexto del cambio

La especificación original desplegaba con **Caddy** (reverse proxy + HTTPS automático) en una
VM Oracle Cloud. El dueño pidió desplegar con **nginx** detrás de **Cloudflare en modo nube
gris (DNS only)**, porque la VM ya hospeda otros proyectos exactamente así: nginx instalado,
puertos 80/443 abiertos, certbot presente y el subdominio `fitness.streamlytics.stream` ya
apuntando a la máquina. Caddy habría duplicado el rol del nginx existente y competido por los
puertos. El resto de la app se construyó conforme a la spec.

---

## 2. Decisiones de despliegue

### ADR-6 · nginx (vhost compartido) en vez de Caddy
- **Decisión:** un `server block` de nginx para el subdominio que hace `proxy_pass` a uvicorn
  en `127.0.0.1:8091`. Se integra con el nginx multi-sitio ya existente.
- **Consecuencia:** un único reverse proxy en la VM; HTTP→HTTPS y cabeceras de seguridad
  centralizadas en nginx. Archivo: [`../deploy/nginx/fitness.streamlytics.stream.conf`](../deploy/nginx/fitness.streamlytics.stream.conf).

### ADR-7 · Cloudflare nube gris (DNS only) + TLS Let's Encrypt en el origen
- **Alternativas consideradas:**
  - *Cloudflare Tunnel (cloudflared):* evita abrir puertos, pero la VM ya los tiene abiertos y
    añadiría un daemon y dependencia extra. Descartado por innecesario.
  - *Nube naranja (proxied) + Origin Certificate:* obliga a gestionar el cert de Cloudflare y a
    restringir a sus rangos de IP. Más piezas para un beneficio (CDN/WAF) que aquí no se necesita.
  - *Nube gris (DNS only) + Let's Encrypt:* **elegida.** El tráfico llega directo al origen, el
    challenge **HTTP-01** de certbot funciona sin trucos, y es idéntico a cómo ya operan los
    otros proyectos del dueño.
- **Consecuencia:** el certificado lo emite Let's Encrypt (no Cloudflare); renovación automática
  vía `certbot.timer`. Cloudflare actúa solo como DNS autoritativo.

### ADR-8 · FastAPI sigue sirviendo el build estático (ADR-2 intacto)
- **Decisión:** nginx **no** sirve `client/dist`; solo reverse-proxya todo a uvicorn, y FastAPI
  monta los estáticos + fallback SPA. Para un único usuario y baja carga, evitar duplicar rutas
  de estáticos en nginx simplifica el deploy y mantiene el single-origin (sin CORS).

### ADR-9 · Puerto de aplicación configurable (8091 por defecto)
- **Decisión:** como la VM corre otros servicios, el puerto se fija en `.env` (`PORT`) y debe
  verificarse libre (`ss -ltnp`). Default `8091` (no `8080` de la spec, más propenso a colisión).
  Debe coincidir en tres sitios: `.env`, el `--port` del service y el `proxy_pass` de nginx.

### ADR-10 · uvicorn con `--proxy-headers` detrás de nginx
- **Problema:** nginx termina TLS y proxya **HTTP** a uvicorn; sin información de proxy, FastAPI
  vería esquema `http` y la cookie de sesión `Secure` podría no comportarse bien.
- **Decisión:** nginx envía `X-Forwarded-Proto $scheme`; uvicorn arranca con
  `--proxy-headers --forwarded-allow-ips 127.0.0.1`. Así el esquema https se respeta de extremo a
  extremo. Implementado en [`../deploy/tablero-entrenador.service`](../deploy/tablero-entrenador.service).

---

## 3. Decisión de implementación que se desvió de la spec

### bcrypt directo en lugar de `passlib[bcrypt]`
- **Motivo:** `passlib` 1.7.4 está sin mantenimiento y rompe con bcrypt 5.x (lee
  `bcrypt.__about__`, eliminado; además falla en su rutina interna `detect_wrap_bug`). En
  Python 3.13 esto impedía hashear contraseñas.
- **Decisión:** usar la librería **`bcrypt`** directamente en
  [`../server/auth.py`](../server/auth.py) (`hashpw`/`checkpw`), truncando a 72 bytes (límite de
  bcrypt). Mismo algoritmo y seguridad que pedía la spec, sin la capa frágil de passlib.

---

## 4. Seguridad (resumen aplicado)

- Cookie de sesión `httpOnly`, `SameSite=Lax`, `Secure` cuando `COOKIE_SECURE=true`, firmada con
  `SESSION_SECRET` (sin secreto la app **no arranca**).
- Sin endpoint de registro; el alta de usuario solo por seed.
- Rate-limit de login en memoria (5 intentos/min por IP) en
  [`../server/routers/auth.py`](../server/routers/auth.py).
- Cabeceras en FastAPI (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`) y en nginx
  (HSTS + las mismas), TLS por Let's Encrypt.
- Validación estricta de `pattern_id`, `level`, `unit`, `better` contra catálogo antes de escribir.
- Backups: `GET /api/export/backup.json` + script cron [`../deploy/backup.sh`](../deploy/backup.sh)
  (retención 14 días, copia consistente con `sqlite3 .backup` aun con WAL activo).

---

## 5. Orden de construcción (hitos) y estado

| Hito | Entregable | Estado |
|---|---|---|
| 0 | Andamiaje (estructura, deps, `.env.example`) | ✅ |
| 1 | Backend núcleo (config, db WAL, models, schemas, logic, auth, main) | ✅ verificado |
| 2 | Routers API §6 (auth, patterns, athletes, routines, tests, sessions, progress, export) | ✅ smoke-test |
| 3 | Seed idempotente §8 (admin, patrones, rutinas, pruebas, 5 alumnos) | ✅ |
| 4 | Frontend React+Vite §7 (6 páginas, componentes, tokens) | ✅ build OK |
| 5 | Deploy nginx + Cloudflare nube gris (vhost, systemd, backup) | ✅ |
| 6 | Tests pytest §13 | ✅ 22 passed |

Verificaciones realizadas durante el desarrollo:
- **Backend end-to-end** (TestClient): login/sesión, catálogo, alumnos con niveles, caso nuclear
  de variantes por alumno (Alumno 3 → jueves/pierna=C, miércoles/tracción=B), dedup e ignorar
  vacíos en sesiones, orden y conversión `num` en progreso, export `.txt`/`.csv`.
- **Stack HTTP real:** uvicorn sirviendo el build de Vite — `/` devuelve `index.html`, cabecera
  `nosniff` presente, login por cookie, assets y fallback SPA (`/progreso`) correctos.
- **Suite pytest:** 22 pruebas en verde.

---

## 6. Pendientes / roadmap (no bloqueantes, §14 de la spec)

- Indicador de semana del bloque de 4 semanas (carga/descarga).
- Reordenamiento drag-and-drop (el endpoint `reorder` ya existe).
- Empaquetar fuentes Oswald/Barlow + Inter localmente (hoy se usa un stack condensado del
  sistema como fallback; los nombres ya están en `tokens.css` para soltar los `.woff2`).
- Import/restore de backup desde la UI (endpoints `backup.json` ya implementados).

> Nota: la **PWA** ya no es pendiente — se implementó en la iteración 2 (ADR-14).

---

## 7. Iteración 2 — medios, CSV, PWA y UI móvil

### ADR-11 · Medio por variante (A/B/C), no por ejercicio
- **Decisión:** `routine_exercises` gana `media_a/b/c`. Como A/B/C suelen ser movimientos distintos,
  cada variante puede tener su propia demostración. En "Por alumno" se resuelve el medio del nivel del
  alumno (igual que el texto). Migración aditiva idempotente en `db.py` (ALTER TABLE si falta la columna),
  porque `create_all` no altera tablas existentes.

### ADR-12 · Subir imagen/gif al servidor + URL para video
- **Decisión:** `POST /api/uploads` guarda imágenes/gifs en `data/uploads/` (servidas en `/media/<x>`,
  incluidas en backups). El video va por **URL externa** (YouTube/Vimeo/mp4) para no almacenar archivos
  pesados. Validación de tipo y tamaño ≤ 5 MB. El front detecta el tipo por extensión/host
  (`lib/media.js`) y elige `<img>`, `<iframe>` (YouTube/Vimeo) o `<video>`.

### ADR-13 · CSV "reemplazar todo" + export como plantilla
- **Decisión:** import/export CSV con el mismo esquema. **Rutinas:** sin FK entrantes → borrado total +
  recreación. **Pruebas:** como las mediciones referencian `test_id`, no se borra a ciegas: se hace
  **upsert por id** y las pruebas ausentes en el CSV se **archivan si tienen mediciones** (o se borran si
  no), preservando integridad. Export con **BOM UTF-8** para que Excel respete acentos; import tolera
  delimitador `,` o `;`.

### ADR-14 · PWA con vite-plugin-pwa e iconos rasterizados
- **Decisión:** `vite-plugin-pwa` (Workbox) genera manifest + service worker. El **shell** se precachea;
  la API es `NetworkOnly` y los medios `CacheFirst`. El logo (pesa + figura corriendo) se diseña como SVG
  (`public/icons/logo.svg`) y se rasteriza a PNG (192/512/maskable-512/apple-touch-180/favicon-32) con un
  script `scripts/gen-icons.mjs` usando **sharp** (`npm run icons`). Los PNG quedan versionados, así que
  `npm run build` no depende de regenerarlos.

### ADR-15 · Navegación inferior fija (mobile-first)
- **Decisión:** la barra de pestañas pasa a **inferior fija** con iconos + etiqueta, áreas táctiles ≥ 44 px
  y `env(safe-area-inset-*)` para notch/gestos. Inputs a 16 px para evitar el zoom automático de iOS.

### Verificación iteración 2
- pytest: **30 pruebas** en verde (migración, uploads rechaza/acepta, `/media` sirve, media en
  `for-athlete`, import/export CSV con BOM y `;`, validación de catálogo).
- Build: `vite-plugin-pwa` genera `sw.js`, `manifest.webmanifest`, `registerSW.js`; FastAPI sirve el
  manifest (`application/manifest+json`), `sw.js` y los iconos; la ruta SPA `/ejercicio/...` cae a `index.html`.
- Logo verificado visualmente (figura roja corriendo sobre una pesa, fondo oscuro redondeado).

---

## 8. Iteración 3 — niveles dinámicos y días configurables

### ADR-16 · Niveles como catálogo relacional + variantes por nivel
- **Problema:** A/B/C estaba cableado (columnas `variant_a/b/c`, `media_a/b/c`, colores `--lvlA/B/C`).
- **Decisión:** catálogo `levels(id,label,color,sort)` (lista global) y tabla `exercise_variants(exercise_id,
  level_id,text,media)` que reemplaza las columnas fijas. Añadir/quitar niveles ya no toca el esquema.
  `athlete_levels.level` guarda el `level_id`. Borrar un nivel reasigna a los alumnos al primero y borra
  sus variantes; no se puede borrar el último.
- **Migración (sin pérdida, automática en `init_db`):** crea `levels` (A→Principiante, B→Intermedio,
  C→Avanzado con sus colores), copia `variant_*`/`media_*` a `exercise_variants`, y añade `weekday`. Las
  columnas legacy quedan inertes. Idempotente: solo corre una vez (guarda por tabla vacía / PRAGMA).

### ADR-17 · Días configurables con `weekday`
- **Decisión:** CRUD completo de días (`POST/DELETE /api/routines/days`, `PUT /days/reorder`, `PATCH` con
  `weekday`). `routine_days.weekday` (0=dom..6=sáb) mapea cada día al calendario; "Hoy" se resuelve por ese
  valor (antes era un literal lunes–viernes). El frontend deriva la lista de días de las claves de
  `routines` ordenadas por `sort`, no de un `DAY_ORDER` fijo.

### ADR-18 · CSV de rutinas con columnas por nivel
- **Decisión:** la CSV de rutinas pasa de `variant_a/b/c` a columnas dinámicas `var_<id>`/`media_<id>`
  (una pareja por nivel) + `weekday`/`day_sort`. El import detecta las columnas de nivel presentes y valida
  que existan en el catálogo. Export con BOM para Excel; sigue siendo reemplazo total.

### Frontend
- `LevelTag` se vuelve una píldora con el `label` y color inline del catálogo (helper `readableOn` elige
  texto negro/blanco por luminancia). Todo `["A","B","C"]` itera ahora `store.levels`. Nueva subpestaña
  **Niveles** (label, color, reordenar, borrar) y gestión de **Días** (nombre, día de calendario, focus,
  reordenar, eliminar, +día) en el Editor; variantes por nivel editables (texto + `MediaPicker`).

### Verificación iteración 3
- pytest: **37 pruebas** en verde (migración de BD vieja, niveles CRUD + reasignación al borrar, días
  CRUD/reorder, variante por nivel en `for-athlete`, CSV con columnas por nivel).
- Migración probada sobre la BD de desarrollo (esquema it.2): niveles renombrados, variantes copiadas,
  `weekday` fijado; el caso nuclear sigue resolviendo (Alumno 3 jueves/pierna → Avanzado → "Búlgara").

> **Deploy:** la migración corre sola al reiniciar el servicio. Hacer `deploy/backup.sh` **antes** del
> `git pull` que traiga estos cambios.
