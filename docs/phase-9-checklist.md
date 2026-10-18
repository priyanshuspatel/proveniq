# Phase 9 checklist

Use this after Phase 8. Do not treat it as done.

## Accounts and DNS

- Choose a domain and create DNS records yourself. This repository does not change DNS.
- Choose where the API and the site will run. No host account was created here.
- Put `CORS_ORIGINS` on the API equal to the site origin. Do not use `*`.
- Build the frontend with `NEXT_PUBLIC_API_URL` set to the public API origin.
- Keep `PROVENIQ_ACCESS_TOKEN` only in the API runtime secret store. Never add it to frontend build args or `NEXT_PUBLIC_` variables.

## Secrets

- Keep Ollama or a real authentication proxy on a private network reachable only from the API. `OLLAMA_API_KEY` may be stored in the host secret manager for that proxy, but it does not secure a public raw Ollama endpoint and the API refuses one.
- Do not commit `.env` or `.env.local`.
- Confirm `gitleaks detect --source . --redact --log-opts=--all` still reports no leaks in Git history.

## Backend

- Set a long random `PROVENIQ_ACCESS_TOKEN` before starting the API. The API must refuse startup when it is missing.
- Build `backend/Dockerfile`. Confirm the image has no Gemma weights and no `.env`.
- Mount a persistent disk at `DATABASE_PATH`.
- Set `APP_ENV=production`.
- Check `GET /api/health/live` and `GET /api/health/ready` from the host.
- Confirm a Postgres URL is still refused until the migration in `docs/deployment.md` is implemented and tested.

## Inference

- Install Ollama on a machine with at least 8 GB of RAM.
- Run `ollama pull gemma2:2b` there. Do not copy the weights into the frontend image.
- Set `OLLAMA_HOST` to that private address.
- Check `GET /api/health/inference` returns the configured model.
- Stop Ollama and confirm extraction returns 503 without a stack trace.

## Frontend

- Build `frontend/Dockerfile` with the public API URL.
- Enter the shared demo credential at the access screen and confirm that it is kept only in browser session storage.
- Open the site, create a project, analyze one example notice, and download a Markdown report.
- Confirm the page does not claim a legal clearance.

The access gate is shared single-operator demo access, not multi-user authentication.
It does not isolate projects between people who know the credential. Use only
demonstration data and do not expose the API publicly until protected-route checks pass.

## Rollback

- Keep the previous images and the database volume.
- Redeploy the previous API image without deleting the volume.

## Still unresolved from Phase 8

- Five high `npm audit` findings remain in the development ESLint chain (`braces@3.0.3` via `eslint-config-next@15.5.28`). Do not run `npm audit fix --force`.
- PostgreSQL is not connected.
- No live deployment was tested.
