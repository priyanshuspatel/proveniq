# LicenseTrail

Read `docs/product-spec.md` before changing behavior. Implement one phase at a time. Do not add a feature the spec does not describe.

## Stack

- `frontend/`: Next.js, TypeScript, Tailwind CSS.
- `backend/`: Python, FastAPI, Pydantic, SQLite.
- Extraction: Gemma through local Ollama only.
- Backend tests: pytest. Frontend tests: the runner chosen when the Next.js app is created.
- Setup commands must work on macOS.

## Boundaries

- `backend/app/api` handles HTTP only.
- `backend/app/extraction` calls Ollama and returns a draft. It does not set review status.
- `backend/app/verification` decides whether a quotation occurs in the supplied license text.
- `backend/app/rules` sets `supported-checks-passed`, `potential-conflict`, `missing-information`, `unsupported-license`, or `manual-review-required`. Precedence and the Pydantic contracts are in `docs/product-spec.md`.
- `backend/app/persistence` reads and writes SQLite.
- `backend/app/reports` renders the handoff export.
- `frontend/` displays the workflow and the report. It does not reimplement the rule engine.

## Model and evidence rules

- Treat model output as untrusted. Validate it with Pydantic. On failure, store no conditions and mark the asset `manual-review-required`.
- Never let Gemma set the final status. Confidence cannot produce `supported-checks-passed`.
- Never invent source details, creator identities, license conditions, or missing values.
- Never merge conflicting labels or intended uses into one chosen answer.
- A quotation counts only when verification finds it in the supplied license text.
- Every extracted condition must reference an evidence record for the same asset. The evidence quotation and verification status must match the condition. Reject a missing, unknown, cross-asset, or mismatched reference. Do not invent an evidence row to fill the gap.
- Do not set `supported-checks-passed` unless a verified `license-label` quotation matches the declared license label and that condition has a valid evidence reference. A verified condition of any other type is not enough.
- A source URL is not fetched and does not authenticate the declared license.
- Keep attribution, NonCommercial, and NoDerivatives as the preliminary screens in `docs/product-spec.md`. Do not treat them as a full reading of the Creative Commons legal codes.
- Keep ShareAlike, `all-rights-reserved`, and `CC-BY-NC-ND-4.0` at `manual-review-required`.
- A CC0 pass covers only the documented checks. The report must disclose unscreened trademarks, patents, moral rights, and third-party rights.
- Labels outside the supported set stay `unsupported-license`.
- Never claim a report guarantees legal compliance. Keep the spec's disclaimer on every export.
- Do not fetch arbitrary URLs or execute content from asset sources.
- Store only the fields listed in the product spec.
- Keep `.env` files, secrets, and SQLite databases out of Git.

## Change discipline

- Add tests for new behavior in the same phase.
- Prefer the smallest dependency that satisfies the spec.
- Do not refactor unrelated code.
