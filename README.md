# LicenseTrail

LicenseTrail helps a freelance designer or a small creative agency organize digital assets and record the license details they declared before client delivery.

The stored review status in this phase is `manual-review-required`. Extraction and the rule engine are not implemented, so the app does not produce a compliance result.

Product behavior is specified in [`docs/product-spec.md`](docs/product-spec.md).

## Layout

```
proveniq/
├── .github/
│   └── copilot-instructions.md
├── docs/
│   └── product-spec.md
├── frontend/          Next.js dashboard
├── backend/           FastAPI project and asset API
├── tests/
├── .gitignore
└── README.md
```

## macOS setup

Use Node.js 20 or newer and Python 3.11 or newer.

```bash
node --version
python3 --version
```

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is at `http://127.0.0.1:8000`. Interactive docs are at `http://127.0.0.1:8000/docs`.

Frontend, in a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The dashboard is at `http://127.0.0.1:3000`.

Checks:

```bash
cd backend && source .venv/bin/activate && pytest
cd frontend && npm run typecheck && npm run lint
```

Extraction calls a local Ollama model. The default is `gemma2:2b`.

```bash
brew install ollama
brew services start ollama
ollama pull gemma2:2b
```

`POST /api/analyze` and `POST /api/assets/{id}/extractions` send the supplied license text to that model. Quotations are kept only when they occur in that text. The response stays `manual-review-required`. The app does not fetch source URLs.

## This phase

- Create a project, reopen it, and delete it.
- Add an asset, edit the declaration, and delete the asset.
- Evidence and rule results are placeholders.
- SQLite is created at the path in `DATABASE_PATH`. That file stays out of Git.
