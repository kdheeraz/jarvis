# Build and Run (Docker)

How to build images and run the Jarvis stack with Docker Compose, in both
development and production modes. Source of truth is the `Makefile` plus
`docker-compose.yaml` / `docker-compose.dev.yaml` /
`docker-compose.override.yaml` at the repo root.

---

## 1. Prerequisites

- Docker Engine 24+ with the Compose v2 plugin (`docker compose`, not
  `docker-compose`).
- `make` (optional — every target below has a raw `docker compose`
  equivalent).
- (Optional) NVIDIA Container Toolkit if you plan to use the `ollama`
  profile, which reserves a GPU device in `docker-compose.yaml:99-105`.

Free host ports: `3000` (frontend), `8000` (backend), `7880-7889/udp`
(WebRTC media). Profile-specific services use additional ports — see
§5.

---

## 2. First-time setup

```bash
cp .env.example .env
```

Edit `.env` and fill in whatever you need:

- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, AWS keys — only the providers
  you actually plan to use.
- `JWT_SECRET_KEY` — change from the default before exposing the app.
- `WEBRTC_HOST_IP` — leave as `127.0.0.1` for local dev. Set to the
  host's reachable IP for non-localhost deployments. See
  `docs/webrtc-flow.md` §6.
- `BACKEND_PORT`, `FRONTEND_PORT` — only if `8000` / `3000` are taken.

`docker-compose.override.yaml` is auto-loaded by Compose and forces
`CONFIG_PATH=/app/config/config.docker.yaml` so in-cluster service names
(`chromadb`, `postgres`, `host.docker.internal` for Ollama) resolve.

---

## 3. Development mode

Hot-reload backend (`uvicorn --reload`) and Vite dev server, source code
mounted into containers.

```bash
make dev                 # backend + frontend + chromadb
make dev-ollama          # adds the ollama service (requires NVIDIA GPU)
```

Raw equivalent:

```bash
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.dev.yaml \
  --profile chromadb \
  up --build
```

What this does:

- Backend uses the `dev` target in `backend/Dockerfile` (installs
  `[dev,voice,rag]` extras + CPU PyTorch wheel).
- Frontend uses the `dev` target in `frontend/Dockerfile` (Node base,
  `npm run dev` on `:3000`). Vite proxies `/api`, `/ws`, `/webrtc` to
  the backend container — see `frontend/vite.config.ts`.
- `./backend`, `./frontend/src`, `./config`, `./data`, `./models` are
  bind-mounted, so edits are picked up live.
- HuggingFace cache persists in the `hf-cache` named volume so STT/TTS
  models don't re-download on every rebuild.

Open http://localhost:3000. The backend is at http://localhost:8000.

---

## 4. Production mode

Builds the optimized images (multi-stage), serves the SPA via nginx, and
runs uvicorn without `--reload`.

```bash
make build               # docker compose build
make up                  # docker compose --profile chromadb up -d
```

Raw equivalent:

```bash
docker compose build
docker compose --profile chromadb up -d
```

What this does:

- Backend uses the `production` target — same wheels minus `[dev]`.
- Frontend uses the `production` target — `npm run build` produces a
  static bundle copied into `nginx:alpine`. nginx config is
  `frontend/nginx.conf` (SPA fallback + reverse proxy for `/api`, `/ws`,
  `/webrtc`).
- Containers run detached (`-d`). View logs with `make logs` or
  `docker compose logs -f [service]`.
- The healthcheck on `backend` (compose lines 25-30) ensures `frontend`
  only starts once `/api/health` returns 200.

After it's up:

```bash
make migrate             # alembic upgrade head, run inside backend
```

Open http://localhost:3000.

---

## 5. Profiles

Compose profiles let you opt into supporting services without editing
the file. From `docker-compose.yaml`:

| Profile | Service | Image | Host port |
| --- | --- | --- | --- |
| `chromadb`  | `chromadb`  | `chromadb/chroma:latest`     | `8100` |
| `opensearch`| `opensearch`| `opensearchproject/opensearch:2` | `9200` |
| `pgvector` / `postgres` | `postgres` | `pgvector/pgvector:pg16` | `5432` |
| `ollama`    | `ollama`    | `ollama/ollama:latest`       | `11434` (needs NVIDIA GPU) |

Pass each profile you want with `--profile`:

```bash
docker compose --profile chromadb --profile postgres up -d
```

`make up` defaults to `chromadb`. `make down` brings down all profiles
together so nothing is left orphaned.

---

## 6. Common commands

```bash
# build a single service
docker compose build backend
docker compose build frontend

# rebuild with no cache (e.g. after dependency changes)
docker compose build --no-cache backend

# tail logs (Make wraps this)
docker compose logs -f
docker compose logs -f backend

# shell into a running container
docker compose exec backend bash
docker compose exec frontend sh        # alpine — no bash

# restart just one service
docker compose restart backend

# stop without removing
docker compose stop

# stop + remove containers (keeps volumes)
make down

# stop + remove containers + volumes (DESTRUCTIVE — wipes db, indexes, models)
make clean
```

---

## 7. WebRTC / voice considerations

The voice feature requires the patched ICE candidate gathering described
in `docs/webrtc-flow.md`. For builds and runs that means:

- Both `docker-compose.yaml` and `docker-compose.dev.yaml` already
  publish `7880-7889:7880-7889/udp` and set `WEBRTC_HOST_IP=127.0.0.1`,
  `WEBRTC_UDP_PORT_MIN=7880`, `WEBRTC_UDP_PORT_MAX=7889`.
- For deployments where the browser is **not** on the same host as the
  Docker daemon, set `WEBRTC_HOST_IP=<public-ip-or-hostname>` in `.env`
  and make sure the firewall forwards UDP `7880-7889`.
- The number of concurrent voice sessions is capped by the size of the
  UDP port range (default 10). Widen it with `WEBRTC_UDP_PORT_MIN/MAX`
  and the matching compose `ports:` entry — or front the deployment
  with a TURN server.
- Voice requires the optional `[voice]` Python extras, which both the
  `dev` and `production` Dockerfile targets install. If you build a
  custom image without them, voice will silently no-op (see
  `backend/app/voice/stream.py:75-80`).

---

## 8. Database migrations

Migrations live under `backend/app/db/migrations/` (alembic). After the
backend is up:

```bash
make migrate
# equivalent to:
docker compose exec backend alembic upgrade head
```

To create a new revision (during development):

```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
```

The default `DATABASE_URL` is SQLite at `./data/jarvis.db` (bind-mounted
from the host). For Postgres, enable the `postgres` or `pgvector`
profile and set `DATABASE_URL=postgresql://jarvis:jarvis@postgres:5432/jarvis`
in `.env`.

---

## 9. Troubleshooting

- **Port already in use** — set `BACKEND_PORT` / `FRONTEND_PORT` in
  `.env`, or stop the conflicting process. The UDP range cannot easily
  be changed without also editing the compose `ports:` entry.
- **Frontend says "voice not supported" / mic icon hangs at "Connecting"**
  — check `docker compose logs backend` for the
  `[voice] WebRTC docker patch applied` line. If absent, `WEBRTC_HOST_IP`
  isn't set. If present but ICE still fails, the host's firewall is
  likely dropping UDP `7880-7889`.
- **Backend healthcheck never passes** — `docker compose logs backend`
  for stack traces. Common causes: missing API keys for the configured
  LLM provider, or the model download failing on first run.
- **`make dev` rebuilds slowly every time** — only the first build is
  slow (Torch wheel + voice extras). Subsequent builds reuse the layer
  cache. The `hf-cache` named volume keeps STT/TTS model downloads
  across rebuilds.
- **Stale container after editing dependencies** — Compose only rebuilds
  on source changes inside the build context. After editing
  `pyproject.toml` or `package.json` run `docker compose build --no-cache <service>`.

---

## 10. File reference

| File | Purpose |
| --- | --- |
| `Makefile` | Convenience targets — wraps `docker compose` |
| `docker-compose.yaml` | Base services (backend, frontend, optional profiles) |
| `docker-compose.dev.yaml` | Dev overrides — bind mounts, `--reload`, dev image targets |
| `docker-compose.override.yaml` | Auto-loaded — pins `CONFIG_PATH` and `host.docker.internal` |
| `backend/Dockerfile` | Multi-stage: `base`, `dev`, `production` |
| `frontend/Dockerfile` | Multi-stage: `base`, `dev`, `build`, `production` (nginx) |
| `frontend/nginx.conf` | Production reverse proxy + SPA fallback |
| `frontend/vite.config.ts` | Dev server proxy rules |
| `config/config.docker.yaml` | In-cluster service hostnames (used by both modes) |
| `.env.example` | Template for required environment variables |
