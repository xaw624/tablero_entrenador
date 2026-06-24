# Despliegue — Tablero del Entrenador

Despliegue en VM (Ubuntu) con **systemd** (Uvicorn) detrás de **nginx**, y el dominio
**`fitness.streamlytics.stream`** servido a través de **Cloudflare en modo nube gris (DNS only)**.
nginx termina TLS con un certificado **Let's Encrypt** emitido por `certbot`.

```
Internet ─DNS (nube gris)─► VM (IP pública)
   :443/:80  nginx (vhost) ── TLS Let's Encrypt, HTTP→HTTPS, proxy + X-Forwarded-Proto
                 │
                 ▼
   127.0.0.1:8091  uvicorn + FastAPI (systemd, --proxy-headers)
                 ├── /api/*    (JSON REST)
                 ├── /assets/* (build Vite)
                 └── /*        (index.html SPA fallback)
                 ▼
        SQLModel ─► data/app.db (SQLite WAL)
```

> **Por qué nube gris y no Cloudflare proxy/Tunnel:** la VM ya hospeda otros proyectos con
> nginx + certbot y los puertos 80/443 abiertos. Mantener Cloudflare en DNS-only deja que
> el tráfico llegue directo al origen, el challenge HTTP-01 de Let's Encrypt funciona sin
> trucos, y no hace falta ningún certificado/origin-cert ni daemon adicional. Ver
> [`../docs/PLAN-Y-DECISIONES.md`](../docs/PLAN-Y-DECISIONES.md).

---

## 0. Requisitos en la VM

- Python 3.12+ (`python3 --version`).
- **Node.js 20 LTS + npm** (para compilar el frontend). El `npm` de `apt` suele ser demasiado viejo para
  Vite 5; instala Node desde NodeSource:
  ```bash
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
  node -v && npm -v        # v20.x / npm 10.x
  ```
  (Alternativa: compilar el frontend en local y subir `client/dist` por `scp`/`rsync`, sin Node en la VM.)
- nginx instalado y funcionando (ya lo está, hospeda otros sitios).
- `certbot` con el plugin de nginx (`sudo apt install certbot python3-certbot-nginx`).
- `sqlite3` (para los backups): `sudo apt install sqlite3`.
- DNS: en Cloudflare, el registro **A** de `fitness.streamlytics.stream` apunta a la IP pública
  de la VM y está en **nube gris (DNS only)**. (Ya configurado.)

---

## 1. Obtener el código

El proyecto vive en el home del usuario `ubuntu`: **`/home/ubuntu/tablero_entrenador`**
(`~/tablero_entrenador`). Si aún no está clonado:

```bash
cd ~
git clone https://github.com/xaw624/tablero_entrenador.git
cd ~/tablero_entrenador
```

> Si más adelante mueves el proyecto a otra ruta, ajusta `WorkingDirectory`/`EnvironmentFile`/`ExecStart`
> en `deploy/tablero-entrenador.service`, `APP_DIR` en `deploy/backup.sh` y el `proxy_pass` no cambia
> (sigue siendo `127.0.0.1:8091`).

## 2. Elegir un puerto libre

El servicio usa `8091` por defecto. Como la VM ya corre otros proyectos, confirma que está libre:

```bash
ss -ltnp | grep ':8091' || echo "8091 libre"
```

Si está ocupado, elige otro (p. ej. `8092`) y cámbialo en **3 sitios coherentes**:
`.env` (`PORT`), `deploy/tablero-entrenador.service` (`--port`) y
`deploy/nginx/fitness.streamlytics.stream.conf` (`proxy_pass`).

## 3. Backend (venv + dependencias + seed)

```bash
cd /home/ubuntu/tablero_entrenador
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edita .env con valores reales:
#   SESSION_SECRET=$(openssl rand -hex 32)
#   ADMIN_EMAIL / ADMIN_PASSWORD  (tu login)
#   COOKIE_SECURE=true            (producción con HTTPS)
#   PORT=8091

python -m server.seed            # crea admin + datos semilla (idempotente)
```

## 4. Frontend (build estático servido por FastAPI)

```bash
cd /home/ubuntu/tablero_entrenador/client
npm ci
npm run build                    # genera client/dist
```

> FastAPI monta `client/dist` y hace fallback de SPA a `index.html`. No hay que servir
> estáticos desde nginx (decisión ADR-2): nginx solo reverse-proxya a uvicorn.

> **PWA:** el build genera `sw.js`, `manifest.webmanifest` y los iconos (ya versionados en
> `client/public/icons/`). `npm ci` instala `sharp` (devDependency, con binarios precompilados para
> Linux); solo necesitas `npm run icons` si cambias el logo. El `client_max_body_size 20m` del vhost
> cubre las subidas de imágenes (≤ 5 MB).

> **Medios subidos:** las imágenes/gifs de ejercicios se guardan en `data/uploads/` y se sirven en
> `/media/<archivo>`. El script `deploy/backup.sh` ya respalda esa carpeta junto a `app.db`.

Comprobación rápida en local de la VM (sin nginx aún):

```bash
cd /home/ubuntu/tablero_entrenador
.venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8091 &
curl -s http://127.0.0.1:8091/api/health     # {"status":"ok"}
curl -sI http://127.0.0.1:8091/ | head -1     # 200 (index.html)
kill %1
```

## 5. Servicio systemd

```bash
sudo cp deploy/tablero-entrenador.service /etc/systemd/system/tablero-entrenador.service
# Revisa User=, WorkingDirectory= y el puerto en el ExecStart.
sudo systemctl daemon-reload
sudo systemctl enable --now tablero-entrenador
systemctl status tablero-entrenador --no-pager
journalctl -u tablero-entrenador -n 30 --no-pager
```

El `ExecStart` arranca uvicorn con `--proxy-headers --forwarded-allow-ips 127.0.0.1`, para que
FastAPI confíe en `X-Forwarded-Proto` de nginx y la cookie de sesión `Secure` funcione tras el proxy.

## 6. nginx (vhost nube gris)

```bash
sudo cp deploy/nginx/fitness.streamlytics.stream.conf \
        /etc/nginx/sites-available/fitness.streamlytics.stream
sudo ln -s /etc/nginx/sites-available/fitness.streamlytics.stream \
           /etc/nginx/sites-enabled/fitness.streamlytics.stream
sudo nginx -t && sudo systemctl reload nginx
```

## 7. TLS con Let's Encrypt (certbot)

Con la nube gris, el challenge HTTP-01 llega directo al origen:

```bash
sudo certbot --nginx -d fitness.streamlytics.stream
sudo nginx -t && sudo systemctl reload nginx
```

certbot rellena las rutas `ssl_certificate*` y el redirect 80→443 en el vhost.
La renovación es automática (`systemctl status certbot.timer`); puedes probarla con
`sudo certbot renew --dry-run`.

> **Alternativa DNS-01 (opcional):** si algún día pones el dominio en naranja (proxied) o
> quieres certificados wildcard, usa el plugin DNS de Cloudflare con un API token y
> `certbot --dns-cloudflare`. No es necesario en el modo nube gris actual.

## 8. Verificación pública

```bash
curl -sI https://fitness.streamlytics.stream | head -5
# Espera: HTTP/2 200, Strict-Transport-Security, X-Content-Type-Options: nosniff
curl -s  https://fitness.streamlytics.stream/api/health   # {"status":"ok"}
curl -sI http://fitness.streamlytics.stream | grep -i location   # redirige a https
```

Abre `https://fitness.streamlytics.stream` en el navegador y entra con `ADMIN_EMAIL`/`ADMIN_PASSWORD`.
Recorre el checklist de [`../docs/PRUEBAS.md`](../docs/PRUEBAS.md).

Confirmaciones del modo nube gris:
- El certificado lo emite **Let's Encrypt** (no Cloudflare). `echo | openssl s_client -connect fitness.streamlytics.stream:443 2>/dev/null | openssl x509 -noout -issuer`.
- En el panel de Cloudflare el registro está en **DNS only** (icono gris).

## 9. Backups

```bash
chmod +x deploy/backup.sh
# Prueba manual:
deploy/backup.sh
# Cron diario a las 03:00 con retención de 14 días:
crontab -e
#   0 3 * * * /home/ubuntu/tablero_entrenador/deploy/backup.sh >> /var/log/tablero-backup.log 2>&1
```

Restauración: descomprime un `app-*.db.gz` sobre `data/app.db` con el servicio detenido,
o usa `POST /api/import/backup.json` desde la app con el JSON de `GET /api/export/backup.json`.

## 10. Actualizaciones (deploy de nuevos cambios)

```bash
cd /home/ubuntu/tablero_entrenador
git pull                                   # o copia los archivos nuevos
source .venv/bin/activate
pip install -r requirements.txt            # si cambiaron deps
python -m server.seed                       # idempotente, seguro de re-ejecutar
cd client && npm ci && npm run build && cd ..
sudo systemctl restart tablero-entrenador
```

## 11. Resolución de problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| 502 Bad Gateway | uvicorn caído o puerto distinto | `systemctl status tablero-entrenador`; revisa `--port` vs `proxy_pass` |
| Login no persiste (vuelve a pedir) | `COOKIE_SECURE=true` sin HTTPS, o falta `--proxy-headers` | Asegura HTTPS por nginx y el `X-Forwarded-Proto` |
| 503 "Frontend no compilado" | falta `client/dist` | `cd client && npm run build` |
| certbot falla HTTP-01 | registro en naranja o puerto 80 cerrado | Pon el registro en **gris**; confirma 80 abierto |
| Arranca y muere | falta `SESSION_SECRET` | Defínelo en `.env` (`openssl rand -hex 32`) |
