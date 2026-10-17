# LicenseTrail

LicenseTrail helps a freelance designer or a small creative agency organize digital assets and export a source-linked license and attribution report before client delivery.

The report records what the user declared and which quotations were found in the supplied license text. It does not guarantee legal compliance.

Product behavior is specified in [`docs/product-spec.md`](docs/product-spec.md).

## Layout

```
proveniq/
├── .github/
│   └── copilot-instructions.md
├── docs/
│   └── product-spec.md
├── frontend/
├── backend/
├── tests/
├── .gitignore
└── README.md
```

`frontend/`, `backend/`, and `tests/` are empty on purpose. Later phases add the Next.js app, the FastAPI app, and tests. Planned backend packages are `api`, `extraction`, `verification`, `rules`, `persistence`, and `reports`.

## This phase

The scaffold is documents and directories only. There is no server to start and no test suite to run.

From the repository root on macOS:

```bash
find . -path ./.git -prune -o -print | sort
```

## Prerequisites for later phases

Install these on macOS before the application phases. Do not run the app commands below until those phases add `package.json` and the FastAPI app.

```bash
node --version
python3 --version
```

Node.js 20 or newer and Python 3.11 or newer are the expected versions.

Ollama serves Gemma on the local machine:

```bash
brew install ollama
brew services start ollama
ollama pull gemma3
```

Use another local Gemma tag by setting `OLLAMA_MODEL` when the backend exists. The default host is `http://127.0.0.1:11434`.

## Commands for later phases

These commands match the planned apps. They fail today because this phase does not create them.

Frontend, after the Next.js app is added:

```bash
cd frontend
npm install
npm run dev
npm test
```

The dev server is expected at `http://127.0.0.1:3000`.

Backend, after the FastAPI app is added:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pytest
```

The API is expected at `http://127.0.0.1:8000`.
