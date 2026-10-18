# Deployment plan

This plan is not a completed deployment. No host, DNS record, or paid service was created from this repository.

Proveniq stays local-first. SQLite is the only connected database. Ollama runs beside the API and is not bundled in the frontend image.

## Processes

| Piece | What runs | Port | Persistence |
| --- | --- | --- | --- |
| Web | Next.js standalone server from `frontend/Dockerfile` | 3000 | None. Asset type metadata stays in each browser. |
| API | `uvicorn app.main:app` from `backend/Dockerfile` | 8000 | SQLite file mounted at `DATABASE_PATH` |
| Database | SQLite file `licensetrail.db` | none | The Docker volume `proveniq-data` or a host directory |
| Inference | Ollama on the host, model `gemma2:2b` | 11434 | Ollama’s own model store, not this repo |

Do not run Gemma inside the Next.js server or a serverless frontend function. Extraction can take up to `OLLAMA_TIMEOUT_SECONDS` (default 60) and may retry once. The API `REQUEST_TIMEOUT_SECONDS` default is 150 so one retry can finish.

## Environment

Set these in the host or container environment. Do not commit real values.

| Variable | Local | Production |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` |
| `DATABASE_PATH` | `./data/licensetrail.db` | `/data/licensetrail.db` |
| `DATABASE_URL` | unset | unset until a Postgres migration exists |
| `CORS_ORIGINS` | `http://127.0.0.1:3000,http://localhost:3000` | the real site origin, never `*` |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | a private address reachable only from the API; raw public Ollama hosts are refused |
| `OLLAMA_MODEL` | `gemma2:2b` | `gemma2:2b` unless you measure another model |
| `OLLAMA_API_KEY` | unset on localhost | optional credential for an actual private authentication proxy; it is not a security boundary by itself |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | `60` or higher if the machine is small |
| `OLLAMA_HEALTH_TIMEOUT_SECONDS` | `3` | `3` |
| `REQUEST_TIMEOUT_SECONDS` | `150` | at least two inference timeouts |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | the public API origin, baked in at frontend build time |

`gemma2:2b` needs roughly 2 GB of free memory and several GB of disk in the Ollama store. A machine with 8 GB of RAM is a practical minimum for the model plus the API.

The API does not implement an Ollama authentication proxy. In production it fails
closed unless `OLLAMA_HOST` is a private or loopback address (including
`host.docker.internal`). Do not put a raw Ollama server on the public internet and do
not treat `OLLAMA_API_KEY` as proof that a proxy validates credentials. If inference
must cross a network boundary, deploy a real private-network/auth-proxy layer and
point `OLLAMA_HOST` at that private endpoint; verify the proxy separately before
setting production traffic.

## Health checks

- `GET /api/health/live` — process is up. Does not touch the database or the model.
- `GET /api/health/ready` — SQLite answers `SELECT 1`.
- `GET /api/health/inference` — Ollama `/api/tags` lists the configured model. Failure is HTTP 503.
- `GET /api/health` — same as liveness, kept for existing checks.

Logs from `proveniq.access` record method, path, status, and duration. They do not record request bodies, license text, or the Ollama key.

## PostgreSQL migration, not done

The API uses Python’s `sqlite3` driver, `PRAGMA foreign_keys`, and `ON CONFLICT`. A Postgres cutover requires:

1. Add a driver such as `psycopg` and keep it out of local development unless `DATABASE_URL` starts with `postgresql://`.
2. Rewrite each statement in `backend/app/persistence/database.py` for Postgres placeholders and conflict syntax.
3. Replace SQLite `rowid` ordering and `executescript` startup with versioned migrations.
4. Copy existing rows from `licensetrail.db` without deleting that file until the copy is checked.
5. Point `DATABASE_URL` at Postgres only after those tests pass. Until then the API refuses a Postgres URL so it cannot pretend to be connected.

## Database durability and data isolation

1. **Hosted SQLite starts fresh on persistent disk:** On Render, `proveniq-data` mounts at `/data`. On first boot, `init_db()` creates all tables cleanly at `/data/licensetrail.db`.
2. **Local data will not automatically transfer:** `backend/data/licensetrail.db` is strictly preserved on the developer machine and is intentionally excluded from the Docker build context via `.dockerignore`. Local records do not automatically appear in hosted environments.
3. **Optional manual seeding:** If you wish to seed the hosted instance with local data, create a backup using `sqlite3 backend/data/licensetrail.db ".backup licensetrail-seed.db"` and upload it out-of-band via SSH or admin restore. Never commit database files to Git.

## Backup

Copy the SQLite file while the original stays in place. Do not delete `licensetrail.db` to make the copy.

```bash
sqlite3 /data/licensetrail.db ".backup /backups/licensetrail-copy.db"
```

On a Mac without Docker, the same command uses `backend/data/licensetrail.db` as the source. Check that the copy opens before you rely on it.

## Rollback

Keep the previous API image and the SQLite volume. To roll back, start the previous image against the same volume. Do not delete the volume as part of a deploy. The frontend image only needs the previous build if `NEXT_PUBLIC_API_URL` changed.

## Compose

`docker-compose.yml` builds the API and web images and mounts a named volume for SQLite. It expects Ollama on the host at `host.docker.internal:11434`. It does not download model weights. These images were not built or run as a live deployment from this pass.
