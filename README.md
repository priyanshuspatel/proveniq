# Proveniq

Proveniq is a local desk for freelance designers and small creative agencies. It keeps a project’s digital assets, the license notice someone pasted, the quotations checked against that notice, and a plain-language screening result before a file is handed to a client.

It does not decide that a use is legal. A stored pass means the recorded checks succeeded. It is not a clearance and not permission to use the asset.

Product rules are in [`docs/product-spec.md`](docs/product-spec.md). A click-through demo is in [`docs/demo-script.md`](docs/demo-script.md).

## Features

- Create, reopen, edit, and delete a project and its assets.
- Paste a license notice. The text is sent only to a local Ollama model.
- Keep a quotation only when that exact string occurs once in the notice.
- Recognize the supported identifiers below, including a few published surface forms such as `CC BY 4.0`, when that exact span occurs once.
- Let a person correct and confirm fields before the rule engine runs.
- Show one of five statuses, with the reasons that produced it.
- Download a Markdown handoff checklist, and print it from the browser.

Supported identifiers: `CC0-1.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC-BY-NC-4.0`, `CC-BY-NC-SA-4.0`, `CC-BY-ND-4.0`, `CC-BY-NC-ND-4.0`, and `all-rights-reserved`.

Statuses, highest precedence first: `unsupported-license`, `potential-conflict`, `missing-information`, `manual-review-required`, `supported-checks-passed`.

`CC-BY-SA-4.0`, `CC-BY-NC-SA-4.0`, `CC-BY-NC-ND-4.0`, and `all-rights-reserved` do not reach `supported-checks-passed` in this version. Anything outside the supported set, including MIT, GPL, Apache, and a studio-written label, is `unsupported-license`.

## Non-goals

- Legal advice, a lawyer-client relationship, or a guarantee of the right to use an asset.
- Accounts, teams, billing, or a hosted service.
- Fetching or executing a source URL, downloading the asset, OCR, or PDF parsing.
- Calling a remote model API. Inference is local Ollama only.
- A PDF library. The report is Markdown. The browser print dialog can save a PDF.
- Treating a creator typed into the form as if the model had extracted it.
- Filling a missing creator, license, or attribution line with a guess.

The report disclaimer is:

> This report is a preliminary checklist. It is not legal advice. This report organizes declarations and checked quotations. It does not guarantee legal compliance or the right to use these assets.

It also states the screening limits: attribution is only a check that some creator or attribution text is present for CC BY labels; NonCommercial and NoDerivatives compare the declared use and do not decide legal NonCommercial purpose or adapted material; ShareAlike, all-rights-reserved, and CC-BY-NC-ND-4.0 stay in manual review; a CC0 pass does not cover trademarks, patents, moral rights, or rights held by other people; a source URL is not fetched and does not authenticate the license.

## Architecture

```
browser (Next.js, port 3000)
    │  JSON over HTTP
    ▼
FastAPI (port 8000) ── SQLite (local file)
    │
    ├── quote check (exact substring, once)
    ├── optional source-span fill for a unique published license name,
    │   "Created by" / "Photograph by" / "Please credit" / "Credit …"
    └── rule engine (deterministic; Gemma does not set the status)
    │
    └── Ollama on 127.0.0.1:11434 (gemma2:2b by default)
```

Data flow for one asset:

1. The browser creates a project and an asset. The asset stores the title, creator, source URL, declared license, pasted notice, intended use, and attribution text. Asset type is kept in this browser only (`localStorage`), not as a server field.
2. Analyze sends the pasted notice to local Ollama at temperature 0. The model must return JSON. A quotation is accepted only when it occurs once in the notice. A claimed license with no verified quotation is retried once. A second failure does not invent a quote.
3. If the model leaves a field empty, the server may add a span that already occurs once: a supported license name, or a creator/credit sentence with one of the cues above. A bare “by …”, a title-case opening line, and a versionless abbreviation such as `CC BY-NC-SA` are not filled in. Two different license names in one notice stay unresolved.
4. The person edits the form and confirms it. Confirming does not run the rules.
5. Run assessment reads the saved asset and stored conditions. It does not call the model. The status follows the precedence above.
6. Download Markdown Report writes a snapshot of every asset on the project. Reload reads that snapshot. It does not run a new assessment.

Opening an asset loads the project, the asset, saved evidence, and the last saved screening with GET requests. It does not POST a new extraction or assessment.

## Prerequisites

- macOS
- Python 3.11 or newer (`python3 --version`)
- Node.js 20 or newer (`node --version`)
- [Ollama](https://ollama.com) for local extraction

No API key is required.

## macOS setup

From the repository root.

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` holds only a local database path, CORS origins, and the local Ollama address. Do not put secrets in it. It is gitignored. The default database file is `backend/data/licensetrail.db`. That filename is kept so an existing local database still opens. The file stays out of Git. Leave `DATABASE_URL` unset. A `postgresql://` URL is refused at startup and is not connected. The queries use SQLite (`PRAGMA foreign_keys`, `ON CONFLICT`). Moving to Postgres would need a new driver and rewritten SQL, which is not implemented.

Frontend, in a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
```

`frontend/.env.local` sets `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`. It is gitignored. `frontend/.env.example` is the template and is safe to commit.

Install the model:

```bash
brew install ollama
brew services start ollama
ollama pull gemma2:2b
```

`ollama list` should show `gemma2:2b`. The weights stay in Ollama’s own store. They are not in this repository.

Start the API:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API: `http://127.0.0.1:8000`. Interactive docs: `http://127.0.0.1:8000/docs`.

Start the dashboard:

```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Dashboard: `http://127.0.0.1:3000`.

Health checks on the API:

- `GET /api/health/live` — the process is up.
- `GET /api/health/ready` — SQLite answers.
- `GET /api/health/inference` — local Ollama has the configured model.
- `GET /api/health` — same response as liveness.

`APP_ENV` is `development`, `test`, or `production`. Production refuses `CORS_ORIGINS=*` and refuses a public Ollama host, even when `OLLAMA_API_KEY` is set: a bearer environment variable is not an authentication proxy. Access logs record the method, path, status, and duration. They do not record license text or the Ollama key. Request bodies and model responses are bounded by configuration.

Optional containers are described in [`docs/deployment.md`](docs/deployment.md). They were not deployed from this repository. The frontend image does not contain Gemma weights. Ollama stays on the host.

If Ollama is not running, extraction returns HTTP 503 `extraction_unavailable`. A timeout returns HTTP 504 `extraction_timeout`. Neither response includes a stack trace. The asset is not given a passing status.

## How inference and the rules differ

Gemma only proposes a license identifier, creator, license URL, attribution line, and quotations. Temperature is 0. The prompt tells the model that the notice is data, not instructions.

The server then checks every quotation with a literal substring search. One occurrence is `verified`. Zero is `not-found`. Two or more is `ambiguous`. An unverified quotation cannot establish a license, creator, or attribution line.

The rule engine does not see the model’s prose. It compares the declared license, the saved intended use, the project’s intended use, whether a verified license quotation matches the declared identifier, and whether creator or attribution text was supplied on the form. Extracted text and typed text stay separate. A conflict between them is not merged.

A pass still leaves trademarks, patents, moral rights, and third-party rights unscreened. CC0 can pass only inside those checks, and the report says so.

## Tests

From the repository root, after installing the backend and frontend dependencies:

```bash
make test
```

This runs both offline suites without starting Ollama. The individual commands below
are useful when iterating on one side of the application.

```bash
cd backend
source .venv/bin/activate
pytest
```

```bash
cd frontend
npm test
npm run typecheck
npm run lint
npm run build
```

`npm test` covers report restore and the download helper. It does not call Ollama. `pytest` covers the API, quote checks, the rule table, and extraction with a mocked model. Live Gemma scores are not part of `pytest`. They are measured with:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python tests/evaluate_notices.py
PYTHONPATH=. python tests/evaluate_heldout.py
```

The first script scores the 27 non-blank notices in `backend/tests/fixtures/license_notices_v1.json`. The blank notice is rejected with HTTP 422 before the model runs. The second script scores 16 held-out notices in `backend/tests/fixtures/license_notices_heldout_v1.json`. Those sentences were not copied from the development set. Both scripts need a running local `gemma2:2b`.

Stop `npm run dev` before `npm run build`. A production build writes the same `.next` directory the dev server uses.

## Evaluation results

Measured locally with `gemma2:2b`, temperature 0, and one repair retry. These are not a general accuracy claim and not a legal benchmark.

Development fixture, version 1, 27 non-blank notices, model plus source-span rules, scored against the labels in that file:

| Check | Result |
| --- | --- |
| License identifier, exact match, `UNKNOWN` included | 27/27 |
| Attribution field | 27/27 |
| Creator name | 18/27 |
| Verified quotation occurs once in the notice | 27/27 |
| Invented creator or attribution | 0 |

The nine creator misses are notices whose only name cue is bare “by …” or a name at the start of the line. Those cues are left empty on purpose.

An earlier scoring change, not an extraction change, relabelled `CC BY 4.0` and `CC BY-NC 4.0` from `UNKNOWN` to the hyphenated identifier once those exact surface forms were accepted. The 27/27 license count did not rise because of that relabel.

Held-out set, 16 notices, same model. Denominators:

- License accuracy and license false-positive rate use all 16 notices. A false positive is a non-`UNKNOWN` identifier other than the label.
- Creator and attribution precision use emitted values. Recall uses labelled non-null values.
- Evidence verification uses verified rows. Each row must occur once in its notice.
- Manual-review rate uses notices whose rule status is not `supported-checks-passed`. Screening supplied no user URL and no user attribution text, so a pass was not expected.

| Metric | Model only | Model plus source-span rules |
| --- | --- | --- |
| Canonical license | 16/16 | 16/16 |
| License false positives | 0/16 | 0/16 |
| Creator precision | no value emitted | 4/4 |
| Creator recall | 0/4 | 4/4 |
| Attribution precision | no value emitted | 1/1 |
| Attribution recall | 0/1 | 1/1 |
| Evidence verification | every verified row occurred once | every verified row occurred once |
| Not `supported-checks-passed` | 16/16 | 16/16 |

The held-out creator recall is four names that use “Created by”, “Photograph by”, or “Please credit”. It is not a general creator score. Model-only left those names and the one credit sentence empty. The span rules filled them. Status counts on that screening setup were 5 `missing-information` and 11 `unsupported-license`.

## Known limitations

- Bare “by [Name]”, “licensed by”, “inspired by”, and a title-case first line are not treated as a creator.
- A deed sentence that describes attribution, NonCommercial use, or a CC0 freedom, without naming one license, stays `UNKNOWN`.
- `CC BY-NC-SA` without a version is not guessed to be 4.0.
- Two license names in one notice are not merged.
- Attribution screening does not check the full CC BY 4.0 credit elements.
- NonCommercial and NoDerivatives screening compare the use selected in the form. They do not decide those legal questions.
- Asset type lives in browser storage. Clearing that storage clears the type. The server copy of the asset remains.
- There is no login, no multi-user separation, and no ownership scope. Anyone who can reach a deployed API can read or change its projects and reports. Treat the hosted configuration as a single-operator demo until an authentication and ownership layer is added.
- The three buttons on the add-asset form are labelled examples. They are not assessments of real files.
- `npm audit` reports five high findings in the development ESLint chain: `eslint-config-next@15.5.28` through `fast-glob`, `micromatch@4.0.8`, and `braces@3.0.3`. Production dependencies (`npm audit --omit=dev`) reported none. There is no compatible Next.js 15 patch. `npm audit fix --force` would downgrade ESLint config to Next.js 14 and should not be used. The risk is a local lint-time denial of service from a deeply nested pattern, not the running server.

## Privacy

License text and the fields you type stay on this computer. Extraction talks to `http://127.0.0.1:11434`. The app does not call a hosted model API and does not send analytics. Source URLs are stored and shown. They are not requested. `.env`, `.env.local`, the SQLite files, `node_modules`, `.venv`, and `.next` are gitignored. Model weights are downloaded by Ollama and are not committed.
