<div align="center">

# 🔍 ProvenIQ

**Local-first license screening for freelance designers & creative agencies**

*Paste a license notice. Get a verified, evidence-backed handoff report — without sending anything to the cloud.*

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-black?logo=next.js)](https://nextjs.org/)
[![Ollama](https://img.shields.io/badge/Inference-Ollama%20%28local%29-white?logo=ollama)](https://ollama.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-See%20notice-lightgrey)]()

</div>

---

> [!IMPORTANT]
> **ProvenIQ is not a legal tool.** A `supported-checks-passed` result means the recorded checks succeeded — it is not legal clearance, not a lawyer-client relationship, and not permission to use an asset. Always consult a qualified attorney for licensing decisions.

---

## What is ProvenIQ?

ProvenIQ is a **local desktop app** that helps freelance designers and small creative agencies organize digital assets and prepare a source-linked license and attribution report before handing files to a client.

You paste a license notice → a local AI model (Gemma 2 via Ollama) extracts candidate conditions and exact quotations → deterministic rules verify each quotation against the original text → you get a clear screening status and a downloadable Markdown checklist. **Nothing leaves your machine.**

```
browser (Next.js, port 3000)
       │  JSON over HTTP
       ▼
FastAPI (port 8000) ── SQLite (local file)
       │
       ├── Quote check (exact substring, once)
       ├── Source-span fill (unique published license name / credit cues)
       └── Rule engine (deterministic — Gemma never sets the status)
       │
       └── Ollama  127.0.0.1:11434  (gemma2:2b by default)
```

---

## ✨ Core Features

| Feature | Details |
|---|---|
| **Project management** | Create, reopen, edit, and delete projects and their assets |
| **License extraction** | Paste any license notice; Gemma extracts conditions and quotations locally |
| **Evidence verification** | A quotation is accepted only when it appears *exactly once* in the notice |
| **Deterministic rules** | Status is set by rules — the AI model cannot override it |
| **Screening status** | One of five statuses with every individual rule result shown |
| **Handoff report** | Download a Markdown checklist; print to PDF from the browser |
| **Privacy-first** | All text stays on-device — no remote model API, no analytics |

### Supported License Identifiers

```
CC0-1.0 · CC-BY-4.0 · CC-BY-SA-4.0 · CC-BY-NC-4.0
CC-BY-NC-SA-4.0 · CC-BY-ND-4.0 · CC-BY-NC-ND-4.0 · all-rights-reserved
```

Published surface forms like `CC BY 4.0` are also recognized when that exact span appears once in the notice.

> Anything outside this set — MIT, GPL, Apache, studio-written labels — is flagged `unsupported-license`. This version does not screen those identifiers.

---

## 🚦 Screening Statuses

Statuses are evaluated in this precedence order (highest first):

| Status | Meaning |
|---|---|
| `unsupported-license` | Declared label is outside the supported screening set |
| `potential-conflict` | Two retained statements disagree; both are kept visible |
| `missing-information` | A required declared field is null |
| `manual-review-required` | Rules cannot screen the case, extraction failed, or a quote didn't verify |
| `supported-checks-passed` | Every applicable rule outcome is `pass` — **not a legal clearance** |

> `CC-BY-SA-4.0`, `CC-BY-NC-SA-4.0`, `CC-BY-NC-ND-4.0`, and `all-rights-reserved` do not reach `supported-checks-passed` in this version.

---

## 🏗️ Architecture & Data Flow

```
1. Create a project and add an asset
   └── title · creator · source URL · declared license · pasted notice · intended use · attribution text

2. Analyze (sends notice to Ollama at temperature 0)
   └── Model returns JSON: candidate conditions + exact quotations
   └── A quotation is accepted only if it appears once in the notice
   └── A claimed license with no verified quotation is retried once

3. Source-span fill (server-side, no model call)
   └── Adds a span that already occurs once: a supported license name,
       or a creator/credit sentence using cues like "Created by" / "Please credit"
   └── Does NOT invent values, guess versions, or fill missing creators

4. Human confirms — edit the form, then click Confirm
   └── Confirming does NOT run rules

5. Run Assessment (reads saved asset + stored conditions)
   └── Does NOT call the model
   └── Assigns one of the five statuses above

6. Download Markdown Report — snapshot of every asset on the project
   └── Reload reads the snapshot; does NOT run a new assessment
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| [Node.js](https://nodejs.org/) | 20 LTS | Frontend |
| [Python](https://python.org/) | 3.12+ | Backend |
| [Ollama](https://ollama.com/) | latest | Local inference |

### 1 — Pull the model

```bash
ollama pull gemma2:2b
```

> `gemma2:2b` needs ~2 GB of free memory and several GB of disk. An 8 GB RAM machine is the practical minimum.

### 2 — Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # edit PROVENIQ_ACCESS_TOKEN
uvicorn app.main:app --reload
```

API is live at **http://127.0.0.1:8000**

### 3 — Frontend

```bash
cd frontend
npm install
cp .env.example .env.local       # NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run dev
```

App is live at **http://localhost:3000**

---

## 🐳 Docker Compose

```bash
export PROVENIQ_ACCESS_TOKEN=<long-random-value>
docker compose up --build
```

Ollama must be running on the **host** at port `11434` with `gemma2:2b` already pulled. Compose does not download model weights.

| Service | Port | Persistence |
|---|---|---|
| `web` (Next.js) | 3000 | None — asset-type metadata stays in browser |
| `api` (FastAPI) | 8000 | SQLite mounted at `/data/licensetrail.db` |
| SQLite | — | Docker volume `proveniq-data` |

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | `production` hardens CORS and Ollama host validation |
| `DATABASE_PATH` | `./data/licensetrail.db` | SQLite file path |
| `CORS_ORIGINS` | `http://127.0.0.1:3000` | Comma-separated allowed origins; never use `*` in production |
| `PROVENIQ_ACCESS_TOKEN` | *(required)* | Shared bearer token for the single-operator access gate |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Private address only — raw public Ollama hosts are refused |
| `OLLAMA_MODEL` | `gemma2:2b` | Model name as listed by `ollama list` |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Per-inference timeout; increase on slow hardware |
| `REQUEST_TIMEOUT_SECONDS` | `150` | Total API timeout; allow at least two inference timeouts |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | API origin baked in at build time |

---

## 🔐 Security & Privacy

- **Access gate:** Every non-health `/api` request requires `Authorization: Bearer <token>`. The backend compares it with `PROVENIQ_ACCESS_TOKEN` using a constant-time comparison. The frontend stores the credential in `sessionStorage` only.
- **No remote model API.** Extraction talks only to `http://127.0.0.1:11434`. No license text or typed fields leave this machine.
- **No analytics.** Source URLs are stored and displayed. They are never fetched.
- **Gitignored:** `.env`, `.env.local`, SQLite files, `node_modules`, `.venv`, `.next`, and model weights.

> [!CAUTION]
> This gate is **not** accounts, sessions, or multi-user authentication. Anyone with the shared credential can read or modify all projects and reports. Use only demonstration data and do not advertise this mode as user isolation.

### Health Endpoints (always public)

```
GET /api/health/live      — process is up
GET /api/health/ready     — SQLite answers SELECT 1
GET /api/health/inference — Ollama lists the configured model (503 on failure)
```

---

## 🧪 Running Tests

### Backend unit tests

```bash
cd backend
source .venv/bin/activate
pytest
```

### Frontend unit tests

```bash
cd frontend
npm test
```

### Extraction evaluation (requires running `gemma2:2b`)

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python tests/evaluate_notices.py     # 27-notice development set
PYTHONPATH=. python tests/evaluate_heldout.py     # 16-notice held-out set
```

### Evaluation Results

**Development fixture — 27 non-blank notices (model + source-span rules)**

| Check | Result |
|---|---|
| License identifier (exact match, `UNKNOWN` included) | 27/27 |
| Attribution field | 27/27 |
| Creator name | 18/27 |
| Verified quotation occurs once in the notice | 27/27 |
| Invented creator or attribution | 0 |

> The 9 creator misses are notices whose only name cue is a bare "by …" or a title-case first line — left empty by design.

**Held-out set — 16 notices (model + source-span rules)**

| Metric | Model only | Model + source-span rules |
|---|---|---|
| Canonical license | 16/16 | 16/16 |
| License false positives | 0/16 | 0/16 |
| Creator precision | — | 4/4 |
| Creator recall | 0/4 | 4/4 |
| Attribution precision | — | 1/1 |
| Attribution recall | 0/1 | 1/1 |
| Evidence verification | ✓ every row | ✓ every row |

---

## ⚠️ Known Limitations

- Bare `"by [Name]"`, `"licensed by"`, `"inspired by"`, and title-case first lines are not treated as a creator.
- A deed sentence describing attribution or NonCommercial use *without* naming a license stays `UNKNOWN`.
- `CC BY-NC-SA` without a version is not guessed to be 4.0.
- Two license names in one notice are not merged.
- Attribution screening does not validate the full CC BY 4.0 credit element set.
- Asset type lives in browser `localStorage`. Clearing storage clears the type; the server copy remains.
- No login, no multi-user separation, no ownership scope.
- The example buttons on the add-asset form are labelled examples — not assessments of real files.
- `npm audit` reports 5 high findings in the dev ESLint chain (`eslint-config-next@15.5.28` → `fast-glob` → `micromatch` → `braces`). **Production dependencies (`--omit=dev`) report none.** No compatible Next.js 15 patch exists; do not run `npm audit fix --force`.

---

## 📋 Non-Goals

ProvenIQ deliberately does **not**:

- Provide legal advice, a lawyer-client relationship, or any guarantee of the right to use an asset
- Manage accounts, teams, or billing
- Fetch or validate a source URL, download assets, run OCR, or parse PDFs
- Call a remote model API (inference is local Ollama only)
- Treat creator text typed into the form as model-extracted evidence
- Fill missing creator, license, or attribution fields with a guess

---

## 📂 Project Structure

```
proveniq/
├── backend/              # FastAPI + SQLite + rule engine
│   ├── app/
│   │   ├── main.py       # App entry point, CORS, health routes
│   │   ├── routers/      # Projects, assets, screening, evidence
│   │   ├── persistence/  # SQLite database layer
│   │   └── services/     # Ollama client, rule engine, span-fill
│   └── tests/            # Pytest unit tests + evaluation scripts
├── frontend/             # Next.js 15 + React 19 + Tailwind CSS 4
│   └── src/
│       ├── app/          # App Router pages
│       └── lib/          # API client, download, restore helpers
├── docs/                 # Product spec, deployment plan, demo script
├── docker-compose.yml
└── Makefile
```

---

## 📄 Report Disclaimer

Every downloaded report includes:

> *This report is a preliminary checklist. It is not legal advice. This report organizes declarations and checked quotations. It does not guarantee legal compliance or the right to use these assets.*

Screening limits are also stated in the report: attribution checks only that some creator or attribution text is present for CC BY labels; NonCommercial and NoDerivatives compare the declared use and do not decide legal purpose or adapted material; a source URL is not fetched and does not authenticate the license.

---

## 📚 Further Reading

| Document | Contents |
|---|---|
| [`docs/product-spec.md`](docs/product-spec.md) | Full data contract, rule definitions, and status semantics |
| [`docs/demo-script.md`](docs/demo-script.md) | Click-through demo walkthrough |
| [`docs/deployment.md`](docs/deployment.md) | Deployment plan, environment variables, backup & rollback |

---

<div align="center">

Made for freelance designers and creative agencies who care about provenance.

</div>
