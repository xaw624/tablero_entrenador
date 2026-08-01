# Catálogo de ejercicios buscable (fuente: wger)

Registro del plan y las decisiones para añadir una **base de ejercicios buscable** al Tablero
del Entrenador. Hasta ahora, al crear un ejercicio el entrenador escribía el nombre a mano y
subía un GIF o pegaba una URL. Este cambio añade un **catálogo predefinido** desde el que
seleccionar, autocompletando nombre, patrón y medio.

Complementa [`PLAN-Y-DECISIONES.md`](PLAN-Y-DECISIONES.md) y la especificación funcional
[`../ESPECIFICACION_Tablero_Entrenador.md`](../ESPECIFICACION_Tablero_Entrenador.md).

---

## 1. Contexto y objetivo

- **Modelo actual:** el ejercicio vive en `RoutineExercise` + `ExerciseVariant` (texto + medio
  por nivel A/B/C). El medio es una URL/GIF que el entrenador sube a `/media/`
  (ver [`../server/routers/uploads.py`](../server/routers/uploads.py) y
  [`../client/src/components/MediaPicker.jsx`](../client/src/components/MediaPicker.jsx)).
- **Objetivo:** ofrecer un catálogo de solo lectura para **seleccionar** ejercicios en vez de
  teclear/subir todo a mano, sin cambiar el modelo de rutinas.

## 2. Decisiones (ADRs)

### ADR-C1 · Fuente de datos: wger
- **Alternativas:** `hasaneyldrm/exercises-dataset` (GIF de Gym Visual, **medio con copyright**,
  descartado por licencia); `free-exercise-db` (dominio público pero **solo inglés**, fotos no
  GIF); **wger** (Creative Commons, **en español**, con imágenes y API pública/autoalojable).
- **Decisión:** wger. Es el único que combina español + licencia limpia + medios + API.
- **Consecuencia:** la cobertura de imágenes es irregular (contenido de comunidad). El diseño
  guarda `source` por fila para poder añadir más adelante un adapter de `free-exercise-db` sin
  rehacer nada.

### ADR-C2 · Catálogo desacoplado (tabla de referencia de solo lectura)
- **Decisión:** tabla `ExerciseCatalog` independiente de `RoutineExercise`. El catálogo es
  fuente; el ejercicio del entrenador se crea copiando datos y sigue siendo editable.
- **Consecuencia:** cero acoplamiento con las rutinas; el catálogo se puede reimportar o vaciar
  sin tocar los datos del entrenador.

### ADR-C3 · Import de una sola vez (no dependencia en runtime)
- **Decisión:** un script CLI (`python -m server.import_catalog`) baja los datos de wger y los
  persiste en la BD local. La app **no** llama a wger en tiempo de ejecución.
- **Consecuencia:** la app funciona sin red y sin depender de la disponibilidad de wger. El
  refresco del catálogo es una acción manual y explícita.

### ADR-C4 · Medios espejados en `/media/` (no hotlink)
- **Decisión:** el import descarga cada imagen una vez a `data/uploads/` (la misma carpeta que
  las subidas del entrenador) y guarda la ruta local `/media/<archivo>`.
- **Consecuencia:** no se depende del servidor de wger ni de que sus URLs cambien; se cumple la
  licencia CC guardando atribución por fila.

### ADR-C5 · Mapeo categoría → patrón best-effort y editable
- **Decisión:** el import traduce la categoría de wger a uno de los 5 patrones
  (empuje/tracción/pierna/carrera/core) con un dict editable. `pattern_id` es **nullable**:
  si no hay mapeo claro (p. ej. "Arms"), el ejercicio aparece igual y el entrenador ajusta el
  patrón al añadirlo.

## 3. Modelo de datos

Tabla nueva en [`../server/models.py`](../server/models.py). `init_db()` la crea vía
`create_all` — **sin migración manual** en `_migrate`.

| Campo | Tipo | Nota |
|---|---|---|
| `id` | str PK | `"wger-<id>"` |
| `name` | str (index) | nombre en español |
| `name_norm` | str (index) | sin acentos, minúsculas (búsqueda) |
| `pattern_id` | str? FK patterns | mapeo best-effort, nullable |
| `category` | str | categoría original de wger |
| `equipment` | str | equipo (coma-separado) |
| `muscles` | str | músculos primarios (coma-separado) |
| `instructions` | str | descripción ES, sin HTML |
| `media` | str | `/media/catalog-wger-<id>.<ext>` |
| `source` | str | `"wger"` |
| `attribution` | str | texto de atribución |
| `license_name` | str | p. ej. `CC-BY-SA 4.0` |
| `created_at` | int | epoch ms |

## 4. Fases de implementación

| # | Entregable | Archivo(s) | Verificación |
|---|---|---|---|
| 0 | Modelo `ExerciseCatalog` | `server/models.py` | Arranca la app; la tabla se crea sola |
| 1 | Script de import | `server/import_catalog.py` | `--limit 50` y revisar resumen |
| 2 | API de búsqueda | `server/routers/catalog.py`, `main.py`, `services.py` | `curl` con sesión devuelve resultados |
| 3 | Componente picker | `client/src/components/CatalogPicker.jsx` | Busca y muestra miniaturas |
| 4 | "+ Desde catálogo" | `client/src/pages/Editor.jsx` | Crea ejercicio con nombre+patrón+medio |
| 5 | "Catálogo" en medio | `client/src/components/MediaPicker.jsx` | Elige solo el medio de una variante |

### Fase 1 — script `import_catalog.py`
1. Resuelve el id de idioma español desde `GET /api/v2/language/` (`short_name == "es"`).
2. Pagina `GET /api/v2/exerciseinfo/?language=<es>&limit=100` siguiendo `next`.
3. Extrae por ejercicio: traducción ES (nombre + descripción), categoría, equipo, músculos,
   imágenes.
4. Limpia el HTML de la descripción → texto plano.
5. Mapea categoría → patrón (`CATEGORY_TO_PATTERN`, editable).
6. Descarga la imagen principal a `data/uploads/catalog-wger-<id>.<ext>` (idempotente).
7. Upsert en `ExerciseCatalog` con `name_norm` normalizado + atribución/licencia.
8. Imprime resumen: total, con imagen, con patrón mapeado.

Uso:
```bash
python -m server.import_catalog --limit 50   # prueba
python -m server.import_catalog              # completo
python -m server.import_catalog --no-images  # solo texto
```

### Fase 2 — API `/api/catalog`
`GET /api/catalog?q=&pattern=&limit=30` (protegido con `require_user`): normaliza `q`
(sin acentos), `LIKE` sobre `name_norm`, filtro opcional por patrón, orden por nombre,
`limit` acotado. Devuelve `[{id, name, pattern_id, media, muscles, equipment, category}]`.

### Fases 3–5 — UI
- `CatalogPicker.jsx`: modal reutilizable con búsqueda debounced, rejilla con miniaturas,
  `onPick(item)` / `onClose`, pie con atribución.
- Editor: botón **"+ Desde catálogo"** → al elegir, `POST` crea el ejercicio (nombre + patrón)
  y `PUT` mete el `media` en cada variante; luego `refreshRoutines()`. Reusa endpoints existentes.
- MediaPicker: botón **"Catálogo"** → abre el picker prefiltrado por el patrón del ejercicio y
  al elegir hace `onCommit(item.media)`.

## 5. Riesgos conocidos
- **Cobertura de imágenes de wger irregular:** el resumen del import cuenta cuántos ejercicios
  quedan con imagen. Si es bajo, `source` permite añadir `free-exercise-db` como segunda fuente.
- **Mapeo "Arms" ambiguo:** queda sin patrón asignado a propósito; se afina en
  `CATEGORY_TO_PATTERN`.

## 6. Bitácora de progreso

- **2026-08-01** — Documento creado. Decisiones cerradas con el dueño: fuente **wger**, UX
  **doble** (botón "desde catálogo" + búsqueda en el MediaPicker), medios **espejados** en
  `/media/`. Inicio de implementación por Fases 0–1.
- **2026-08-01** — Fases 0–5 implementadas y verificadas:
  - Modelo `ExerciseCatalog` (create_all lo crea, sin migración manual).
  - `import_catalog.py` probado con `--limit 50`: de 50 vistos, **50 importados**, **44 en
    español** (88%), **27 con imagen espejada** (54%) → confirma la cobertura de imágenes
    irregular de ADR-C1. wger expone 828 ejercicios en total.
  - API `/api/catalog` verificada por `TestClient` (200; búsqueda insensible a tildes/mayúsculas
    y filtro por patrón OK).
  - UI: `CatalogPicker` + botón "+ Desde catálogo" en el Editor + botón "Catálogo" en el
    MediaPicker (prefiltrado por patrón). `npm run build` OK; **37 tests backend en verde**.
  - **Pendiente operativo:** correr el import completo (`python -m server.import_catalog`) en el
    servidor de despliegue para poblar el catálogo en producción.
