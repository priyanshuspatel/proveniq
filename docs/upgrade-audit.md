# Proveniq product upgrade audit

Audit date: 2026-10-19

## Baseline and preservation

The repository already contains a working Next.js 15 frontend, a FastAPI/Pydantic
backend, SQLite persistence, local Ollama extraction, deterministic screening rules,
immutable Markdown reports, Docker files, and Render configuration. The existing
uncommitted changes add health checks, runtime validation, request logging, inference
headers, SQLite URL guards, and regression coverage; those changes are preserved.

Baseline checks run before this upgrade:

- Backend: `./.venv/bin/pytest` from `backend/` — **98 passed**.
- Frontend: `npm test` from `frontend/` — **9 passed**.
- Frontend: `npm run typecheck`, `npm run lint`, and `npm run build` — **passed**.
- Docker build/run — **not run** because Docker is not installed in this workspace.

## What already works

- Projects and assets can be created, edited, reopened, and deleted through real API
  calls and persisted SQLite rows.
- Extraction is schema-constrained and every accepted quotation is checked against
  the supplied notice using an exact, unique substring match.
- The model cannot set the final review status; the rules engine owns statuses and
  precedence.
- Unsupported, conflicting, incomplete, and manual-review cases are represented
  separately and reports retain a snapshot rather than changing after later edits.
- Ollama failures return non-success API responses without a fabricated assessment.
- Health checks distinguish process, SQLite, and inference availability.

## Prioritized findings

### P0 — reliability and trust

1. **Analyze can use stale saved fields.** The asset detail page sends the extraction
   request for the last persisted asset while showing unsaved form values. A user can
   believe the visible notice was analyzed when the server analyzed an older one.
2. **Assessment freshness is not obvious in project lists.** The API exposes only the
   last asset status, while the saved screening endpoint carries the authoritative
   `outdated` flag. The workspace needs a clear current/stale/manual-review state.
3. **Report history is not discoverable.** Reports are immutable and retrievable by id,
   but there is no project report list. A generated report is therefore easy to lose
   after leaving the print view.
4. **Request and model-response limits are incomplete.** Pydantic limits fields, but
   there is no bounded HTTP body guard or bounded Ollama response read. Add safe limits
   without changing the 200,000-character license-text contract.
5. **The demo has no authentication or ownership isolation.** This is an intentional
   MVP boundary, but the UI and deployment documentation must state that a publicly
   reachable API exposes all projects and reports to anyone who can call it.

### P1 — core workflow and product quality

1. The dashboard and project workspace are sparse and do not show persisted asset
   counts, status summaries, recent report versions, search, or a useful first-use
   explanation.
2. The project page has no project edit form and report generation provides no history
   or status summary.
3. Asset screens use plain text for status and evidence verification, and the report
   detail view is a raw Markdown `<pre>`, which is hard to scan and less credible as a
   client handoff.
4. The shared visual system is only partially established: status colors, surfaces,
   controls, spacing, and responsive layouts need consistent tokens and components.
5. Some actions do not provide a recoverable error path (notably asset deletion), and
   duplicate submissions are only partially prevented.

### P2 — release quality and reproducibility

1. Frontend tests currently cover helper functions but not the important page behavior
   or the stale-analysis/error flows.
2. Backend tests do not yet cover the new request-size boundary, project report listing,
   report-summary serialization, and configuration edge cases.
3. The repo needs explicit runtime pins, a root offline `make test` command, and a
   backend dependency lock artifact in addition to the existing pinned requirements.
4. The standalone frontend Dockerfile expects a `public/` directory that is not present
   in the repository; Docker is unavailable locally, so this must be fixed and then
   verified in CI or on a machine with Docker.
5. `npm test` emits Node's typeless-module warning; adding the appropriate package
   metadata will make the check quieter and more reproducible.

## Upgrade scope selected

This pass focuses on the highest-value local changes that can be verified without
credentials or a live Ollama model: make the visible workflow use current data, add
real report history and project summaries, introduce reusable accessible UI states and
status treatments, strengthen bounded request handling, add tests, and document the
remaining no-auth/demo and Docker-verification limitations. The SQLite schema and
local Ollama architecture remain unchanged.
