# LicenseTrail product spec

## Summary

LicenseTrail helps freelance designers and small creative agencies organize digital assets and prepare a source-linked license and attribution report before client delivery.

The report is a rules-based screening packet. It records what the user declared, which quotations were found in the supplied license text, and which checks did not pass. It does not guarantee legal compliance, clearance, or the right to use an asset.

This document is the data contract for the MVP. Application code is not part of this phase.

## Users

- A freelance designer preparing files for a client.
- A small creative agency doing the same handoff.

The MVP is a local, single-operator app. It has no accounts, passwords, or stored email addresses.

## Core workflow

1. Create a project.
2. Add an asset, including creator and source URL when the user has them.
3. Supply the declared license label and the license text.
4. Declare the intended use on the project and, separately, on the asset.
5. Ask Gemma, through local Ollama, to extract candidate conditions and exact quotations from the supplied license text.
6. Check each quotation against that supplied text and record character offsets only when the match is unambiguous.
7. Run the deterministic rules. Keep every rule result. Do not merge conflicts into one confident answer.
8. Show the asset review status together with the individual rule results.
9. Export an immutable, evidence-backed handoff report.

## Screening limits

These limits are part of the contract.

- An extracted quotation is evidence only after it is found in the supplied license text. The model does not verify its own quotes.
- A source URL is a user-supplied reference. The app does not fetch it. The URL does not prove that the declared license is authentic, and it is never stored as verified evidence.
- `extraction_confidence` is stored when the model supplies it. A high score does not establish legal correctness and cannot move an asset to `supported-checks-passed`.
- Missing values stay null. The app does not guess a creator, a license label, a URL, an intended use, a quotation, or a confidence score.
- Conflicting labels and conflicting intended uses are both retained. The app does not pick a winner.
- License interpretation is limited to the rule list in this spec. Anything the rules do not cover stays `manual-review-required`.

Gemma never sets `review_status`.

## Allowed statuses

### Asset review status

`Asset.review_status` is exactly one of:

| Status | Meaning |
| --- | --- |
| `supported-checks-passed` | Every applicable rule outcome is `pass`, including `declared-vs-extracted-label`. That rule passes only when a verified `license-label` quotation matches the declared label. This is not a legal clearance. |
| `potential-conflict` | Two retained statements disagree. Both stay visible. |
| `missing-information` | A required declared field is null. |
| `unsupported-license` | The declared label is outside the supported screening set. |
| `manual-review-required` | The rules cannot screen the case, extraction failed, or a quotation did not verify. |

`supported-checks-passed` is allowed only when no rule has any other outcome. A pass from `quotes-verified`, or from any verified condition that is not a matching `license-label`, does not satisfy `declared-vs-extracted-label`. The five status names and this precedence are unchanged.

When several outcomes apply, the asset status is the first match in this order, and every `RuleResult` is still returned:

1. `unsupported-license`
2. `potential-conflict`
3. `missing-information`
4. `manual-review-required`
5. `supported-checks-passed`

### Rule outcome

A rule outcome is `pass`, `potential-conflict`, `missing-information`, `unsupported-license`, or `manual-review-required`. Rules use `pass`. Only the asset status uses `supported-checks-passed`.

### Verification result

| Value | Meaning |
| --- | --- |
| `verified` | The quotation occurs once, exactly, in the supplied license text. |
| `not-found` | The quotation is absent from that text. |
| `ambiguous` | The quotation occurs more than once, so offsets are not stored. |
| `offset-mismatch` | A model-supplied offset does not point at that quotation. |
| `empty-quote` | The quotation is empty or whitespace. |
| `not-authenticated` | Used only for a user-supplied source URL. The URL was not fetched. |

`ambiguous` and `offset-mismatch` are not treated as `verified`.

## Enumerations

### Intended use

- `client-delivery-as-is`
- `client-delivery-modified`
- `commercial`
- `noncommercial`

The project requires one of these four. The asset may omit intended use. Omission is stored as null, not copied from the project, and the `intended-use-present` rule returns `missing-information`.

### Supported license labels

Screening rules exist only for:

- `CC0-1.0`
- `CC-BY-4.0`
- `CC-BY-SA-4.0`
- `CC-BY-NC-4.0`
- `CC-BY-NC-SA-4.0`
- `CC-BY-ND-4.0`
- `CC-BY-NC-ND-4.0`
- `all-rights-reserved`

Any other non-empty label, including `custom` and `unknown`, is stored verbatim and yields `unsupported-license`. The app does not interpret that text.

### Condition type

- `license-label`
- `attribution-required`
- `commercial-use`
- `derivative-works`
- `share-alike`
- `warranty-disclaimer`
- `other`

`normalized_meaning` is limited to `allowed`, `disallowed`, `required`, `not-evaluated`, or null. A meaning outside that set is stored as null and the condition type `other`. The app does not invent a meaning.

## Entities

Server-generated ids are UUID strings. Timestamps are ISO-8601 UTC. Clients cannot set ids, timestamps, or review status.

### Project

| Field | Constraint |
| --- | --- |
| `id` | Primary key, UUID, server-generated |
| `name` | Required, 1–200 characters after trim |
| `client_label` | Optional, 1–200 characters, or null |
| `declared_intended_use` | Required intended-use value |
| `created_at` | Server clock, immutable |

### Asset

| Field | Constraint |
| --- | --- |
| `id` | Primary key, UUID |
| `project_id` | Required foreign key to `projects.id` |
| `title` | Required, 1–300 characters after trim |
| `creator` | Optional, 1–200 characters, or null |
| `source_url` | Optional absolute `http` or `https` URL, 2048 characters maximum, or null |
| `declared_license` | Required, 1–120 characters, stored verbatim |
| `supplied_license_text` | Optional, 1–200000 characters, or null |
| `intended_use` | Optional intended-use value, or null |
| `attribution_text` | Optional, 1–2000 characters, or null |
| `review_status` | Required review status, server-set |

Blank strings are not stored. A blank optional field becomes null. A blank required field is a validation error.

### ExtractedCondition

| Field | Constraint |
| --- | --- |
| `id` | Primary key, UUID |
| `asset_id` | Required foreign key |
| `condition_type` | Required condition type |
| `normalized_meaning` | Allowed meaning, or null |
| `exact_supporting_quotation` | Required raw model string, may later fail verification |
| `quote_start` | Nullable integer, Unicode code point offset into `supplied_license_text` |
| `quote_end` | Nullable integer, exclusive offset |
| `extraction_confidence` | Nullable number from 0 through 1. Missing stays null |
| `verification_result` | Required verification result other than `not-authenticated` |
| `evidence_record_id` | Required foreign key to `evidence_records.id` |

Every condition references exactly one evidence row. The evidence row is the explicit source for that condition's quotation. Offsets are server-computed. Both are null, or `0 <= quote_start < quote_end <= len(text)`. They are set only when the exact quotation occurs once. Model-supplied offsets are checked and then discarded from the stored contract; a mismatch sets `offset-mismatch`.

The referenced evidence row must:

- exist
- have the same `asset_id` as the condition
- have non-null `source_text` copied from the asset's supplied license text
- have `quotation` equal to `exact_supporting_quotation`
- have `verification_status` equal to the condition's `verification_result`

A URL-only evidence row (`source_reference` set, `source_text` null, `not-authenticated`) cannot be the source of a condition. One evidence row is referenced by at most one condition.

### EvidenceRecord

| Field | Constraint |
| --- | --- |
| `id` | Primary key, UUID |
| `asset_id` | Required foreign key |
| `source_text` | Snapshot of the supplied license text, or null |
| `source_reference` | User-supplied URL, or null |
| `quotation` | Quotation this row supports, or null on a URL row |
| `verification_status` | Required verification result |

At least one of `source_text` and `source_reference` is non-null. A row is never both a verified quotation and a URL authentication. A verified quote references `source_text` only. A URL row uses `source_reference`, a null quotation, and `not-authenticated`.

### RuleResult

| Field | Constraint |
| --- | --- |
| `id` | Primary key, UUID |
| `asset_id` | Required foreign key |
| `rule_id` | Required stable identifier from the rule list |
| `outcome` | Required rule outcome |
| `explanation` | Required, 1–500 characters, describes the screening result |
| `extracted_condition_id` | Optional foreign key |
| `evidence_record_id` | Optional foreign key |

### Report

| Field | Constraint |
| --- | --- |
| `id` | Primary key, UUID |
| `project_id` | Required foreign key |
| `generated_at` | Server clock |
| `included_asset_ids` | Every asset on the project at generation time, in creation order |
| `report_version` | Integer, starts at 1, unique per project |
| `snapshot` | Immutable JSON copy of the project, assets, conditions, evidence, and rule results |
| `disclaimer` | The fixed sentence below |

> This report organizes declarations and checked quotations. It does not guarantee legal compliance or the right to use these assets.

The report also includes the limitations notice in Screening limitations. That notice is part of `disclaimer` together with the sentence above.

Later edits do not change an existing report.

## Database constraints

SQLite. Foreign keys are enforced. Child rows use `ON DELETE CASCADE` from the asset or project that owns them. Deleting a project deletes its assets and reports.

- `projects.id` primary key.
- `projects.name` non-null. Application code rejects blank names.
- `projects.declared_intended_use` non-null and inside the intended-use enumeration.
- `assets.project_id` non-null references `projects.id`. Index on `project_id`.
- `assets.review_status` non-null and inside the review-status enumeration.
- `assets.declared_license` non-null.
- `extracted_conditions.extraction_confidence` is null or between 0 and 1 inclusive.
- `extracted_conditions` offsets are both null or a valid half-open range.
- `extracted_conditions.evidence_record_id` is non-null, unique, and references `evidence_records.id` with `ON DELETE RESTRICT`. Deleting a referenced evidence row is rejected while the condition exists.
- `evidence_records` check: `source_text IS NOT NULL OR source_reference IS NOT NULL`.
- A condition insert is rejected unless the referenced evidence row exists. SQLite foreign keys enforce that existence and `ON DELETE RESTRICT`.

### Application-level evidence validation

SQLite foreign keys do not compare columns across the two rows. The application must reject the insert before it is attempted when any of these checks fail:

- The evidence row's `asset_id` differs from the condition's `asset_id`.
- `source_text` is null, including a URL-only row.
- `quotation` differs from `exact_supporting_quotation`.
- `verification_status` differs from the condition's `verification_result`.

Those failures return `422` `validation_error` and store no condition row. A missing `evidence_record_id` is the same `422`. An id that is not in `evidence_records` returns `404` `not_found` and stores no condition row. The application must not coerce a missing reference into a new evidence row or a passing status.
- `reports` unique `(project_id, report_version)`.
- Included asset ids are also stored in `report_assets(report_id, asset_id)` with a unique pair, matching the snapshot.

No uniqueness constraint on asset title or source URL. Two assets may share a title.

## Rules

Each rule writes one `RuleResult`. Explanations state the comparison that was made.

| `rule_id` | Passes when | Otherwise |
| --- | --- | --- |
| `declared-license-supported` | Label is in the supported set | `unsupported-license` |
| `license-text-present` | `supplied_license_text` is non-null | `missing-information` |
| `source-reference-present` | `source_url` is non-null | `missing-information` |
| `intended-use-present` | Asset `intended_use` is non-null | `missing-information` |
| `attribution-present` | Label is not `CC-BY-*`, or creator or attribution text is present | `missing-information` for a `CC-BY-*` label with both null |
| `project-vs-asset-intended-use` | Asset use is null or equal to the project use | `potential-conflict` when both are set and differ |
| `declared-vs-extracted-label` | At least one `license-label` condition exists, every `license-label` condition is `verified`, and each of those quotations contains exactly one supported label equal to `declared_license` | `potential-conflict` when any verified `license-label` quotation contains exactly one supported label and it differs from `declared_license`. `manual-review-required` when no `license-label` condition exists, any `license-label` condition is `not-found`, `ambiguous`, `offset-mismatch`, or `empty-quote`, or a verified quotation contains no supported label or more than one. A longer supported label is one label: `CC-BY-NC-4.0` does not also count as `CC-BY-4.0`. `normalized_meaning` is not compared. A verified `warranty-disclaimer`, `attribution-required`, or any other non-label condition cannot make this rule pass |
| `nc-vs-declared-use` | Label is not `*-NC*`, or asset `intended_use` is null, or asset `intended_use` is `noncommercial` | `potential-conflict` only when the label is `*-NC*` and asset `intended_use` is `commercial`, `client-delivery-as-is`, or `client-delivery-modified` |
| `nd-vs-declared-use` | Label is not `*-ND*`, or asset `intended_use` is null, `commercial`, or `noncommercial` | `potential-conflict` when the label is `*-ND*` and asset `intended_use` is `client-delivery-modified`. `manual-review-required` when the label is `*-ND*` and asset `intended_use` is `client-delivery-as-is`, because that value does not reliably establish that no Adapted Material is shared |
| `source-url-not-authentication` | A URL row exists or the URL is null | Always `pass`. Explanation says the URL was not fetched and does not authenticate the license |
| `extraction-completed` | A schema-valid extraction has been stored for the current license text | `manual-review-required` when extraction has not been run, the model JSON was unusable, or the model returned no conditions |
| `quotes-verified` | At least one condition is stored and every condition is `verified` | `manual-review-required` |
| `restrictive-label-not-screened` | Label is not `all-rights-reserved`, `CC-BY-SA-4.0`, `CC-BY-NC-SA-4.0`, or `CC-BY-NC-ND-4.0` | `manual-review-required` |

Unsupported labels still record the field-presence rules so missing text and missing attribution remain visible. Those extra outcomes do not replace `unsupported-license` as the asset status.

`CC0-1.0` does not require attribution. `all-rights-reserved`, `CC-BY-SA-4.0`, `CC-BY-NC-SA-4.0`, and `CC-BY-NC-ND-4.0` do not reach `supported-checks-passed` in this MVP.

A verified quotation does not overwrite `declared_license`. Confidence is not an input to any rule.

`declared-vs-extracted-label` is the license-label pass gate. The quotation matches the declared label when a whole-label scan of `exact_supporting_quotation` finds exactly one supported label and that label is equal to `declared_license`. Absence, an unverified quotation, an ambiguous quotation, or a contradictory verified label means this rule is not `pass`. The asset then cannot be `supported-checks-passed`. A verified condition of any other type is not sufficient. Existing precedence still chooses the asset status when another rule has a higher outcome.

## Screening limitations

These limits are part of the contract. A pass means the checks below succeeded. It does not mean the use is lawful.

### Attribution

`attribution-present` is a preliminary screen. For a `CC-BY-*` label it checks that `creator` or `attribution_text` is non-null. It does not check the elements required when material is shared under [CC BY 4.0, Section 3(a)(1)](https://creativecommons.org/licenses/by/4.0/legalcode.en): creator identification, a copyright notice, a license notice, a warranty-disclaimer notice, a URI when the licensor supplied one, a modification indication, and a statement of the license. Those elements were read from that legal code. This screen does not decide that they are present.

### NonCommercial and NoDerivatives

`nc-vs-declared-use` and `nd-vs-declared-use` are conservative screens. They compare the declared `intended_use` enum. They do not determine whether a use is NonCommercial under [CC BY-NC 4.0, Section 1(i)](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en), or whether material is Adapted Material under [CC BY-ND 4.0, Section 1(a) and Section 2(a)(1)](https://creativecommons.org/licenses/by-nd/4.0/legalcode.en).

- `commercial` with an `*-NC*` label is `potential-conflict`.
- Either client-delivery value with an `*-NC*` label is `potential-conflict`, because those values are not a reliable NonCommercial classification.
- `client-delivery-modified` with an `*-ND*` label is `potential-conflict`.
- `client-delivery-as-is` with an `*-ND*` label is `manual-review-required`, because that value does not reliably establish that no Adapted Material is shared.
- A null intended use stays `missing-information`. The screen does not invent a class.
- `noncommercial` with an `*-NC*` label can pass this one rule. That means the user declared `noncommercial`. It does not verify monetary compensation or primary intent.
- `commercial` or `noncommercial` with an `*-ND*` label can pass this one rule. That means the user did not select `client-delivery-modified`. It does not verify that the work is unmodified.

`CC-BY-NC-ND-4.0` cannot receive `supported-checks-passed` until these two screens are defined and reviewed further. `restrictive-label-not-screened` keeps it at `manual-review-required`.

### ShareAlike and all-rights-reserved

`CC-BY-SA-4.0`, `CC-BY-NC-SA-4.0`, and `all-rights-reserved` stay at `manual-review-required`. The spec does not implement [CC BY-SA 4.0, Section 3(b)](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en). `all-rights-reserved` is not one of the Creative Commons legal codes cited here. There is no relicense field and no permission field.

### CC0

`CC0-1.0` may reach `supported-checks-passed` only when every applicable rule passes, including a matching verified `license-label` quotation and its evidence reference. Within that scope, the waiver text read in [CC0 1.0, Section 2](https://creativecommons.org/publicdomain/zero/1.0/legalcode) imposes no attribution condition, so a null creator and null attribution text do not block this label. The pass does not cover trademarks, patents, moral rights, or rights held by other people. Those limits are in CC0 Section 4 and are unscreened.

The handoff report always includes the existing disclaimer and this limitations notice:

> Attribution screening checks only that a creator or attribution text is present for CC-BY labels. NonCommercial and NoDerivatives screening compares the declared intended use and does not determine legal NonCommercial purpose or Adapted Material. ShareAlike, all-rights-reserved, and CC-BY-NC-ND-4.0 stay in manual review in this version. A CC0 pass covers only the checks in this specification. It does not cover trademarks, patents, moral rights, or rights held by other people. A source URL was not fetched and does not authenticate the license.

Extraction is skipped when `supplied_license_text` is null. No condition rows are invented. After a requested extraction, malformed model JSON produces no conditions and `extraction-completed` returns `manual-review-required`. There is no separate `extraction-unusable` rule id.

## API

JSON over HTTP. Request models use Pydantic v2 with `extra = "forbid"`. Unknown fields, including a client-supplied `review_status`, are validation errors. Optional fields that are omitted or JSON null stay null. The API does not coerce a missing license, creator, or confidence into a placeholder.

Path ids that are not UUIDs are validation errors. Unknown ids are `404`.

### Error body

```python
class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, str]] = []
```

| HTTP | `code` | When |
| --- | --- | --- |
| 400 | `malformed_json` | Body is not JSON |
| 422 | `validation_error` | JSON parsed, but a request model rejected it |
| 404 | `not_found` | Project, asset, report, or evidence id does not exist |
| 409 | `missing_source_text` | Extraction was requested and `supplied_license_text` is null |
| 422 | `validation_error` | A condition write omits `evidence_record_id`, points at a URL-only evidence row, points at another asset, or the evidence quotation or verification status differs from the condition |
| 503 | `extraction_unavailable` | Ollama could not be reached. No guessed conditions are stored |

A domain review status is not an HTTP error. A valid asset with missing attribution is `201` or `200` and `review_status = "missing-information"`.

### Routes

| Method and path | Request | Response |
| --- | --- | --- |
| `POST /api/projects` | `ProjectCreate` | `201` `ProjectRead` |
| `GET /api/projects/{project_id}` | — | `200` `ProjectRead` |
| `GET /api/projects` | — | `200` `list[ProjectRead]` |
| `PATCH /api/projects/{project_id}` | `ProjectUpdate` | `200` `ProjectRead` |
| `DELETE /api/projects/{project_id}` | — | `204` |
| `POST /api/projects/{project_id}/assets` | `AssetCreate` | `201` `AssetRead` |
| `GET /api/projects/{project_id}/assets` | — | `200` `list[AssetRead]` |
| `GET /api/assets/{asset_id}` | — | `200` `AssetRead` |
| `PATCH /api/assets/{asset_id}` | `AssetUpdate` | `200` `AssetRead` |
| `DELETE /api/assets/{asset_id}` | — | `204` |
| `POST /api/assets/{asset_id}/extractions` | empty object | `200` `ExtractionRead` |
| `POST /api/assets/{asset_id}/screening` | empty object | `200` `ScreeningRead` |
| `GET /api/assets/{asset_id}/evidence` | — | `200` `list[EvidenceRecordRead]` |
| `POST /api/projects/{project_id}/reports` | empty object | `201` `ReportRead` |
| `GET /api/reports/{report_id}` | — | `200` `ReportRead` |

`POST` and `PATCH` that change an asset run screening before the response is returned. Extraction persists an evidence row and its condition together, then runs screening. A condition is not stored, and no partial condition from that attempt is kept, when its evidence reference is missing or invalid. A failed model parse still returns `200` with `conditions: []` and `manual-review-required`.

Evidence reference errors:

| Situation | HTTP | What is stored |
| --- | --- | --- |
| `evidence_record_id` omitted or null | `422` `validation_error` | No condition row |
| `evidence_record_id` not in `evidence_records` | `404` `not_found` | No condition row |
| Evidence row belongs to another asset, has null `source_text`, has a different quotation, or has a different verification status | `422` `validation_error` | No condition row |

### Pydantic contracts

```python
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewStatus(str, Enum):
    SUPPORTED_CHECKS_PASSED = "supported-checks-passed"
    POTENTIAL_CONFLICT = "potential-conflict"
    MISSING_INFORMATION = "missing-information"
    UNSUPPORTED_LICENSE = "unsupported-license"
    MANUAL_REVIEW_REQUIRED = "manual-review-required"


class RuleOutcome(str, Enum):
    PASS = "pass"
    POTENTIAL_CONFLICT = "potential-conflict"
    MISSING_INFORMATION = "missing-information"
    UNSUPPORTED_LICENSE = "unsupported-license"
    MANUAL_REVIEW_REQUIRED = "manual-review-required"


class IntendedUse(str, Enum):
    CLIENT_DELIVERY_AS_IS = "client-delivery-as-is"
    CLIENT_DELIVERY_MODIFIED = "client-delivery-modified"
    COMMERCIAL = "commercial"
    NONCOMMERCIAL = "noncommercial"


class ConditionType(str, Enum):
    LICENSE_LABEL = "license-label"
    ATTRIBUTION_REQUIRED = "attribution-required"
    COMMERCIAL_USE = "commercial-use"
    DERIVATIVE_WORKS = "derivative-works"
    SHARE_ALIKE = "share-alike"
    WARRANTY_DISCLAIMER = "warranty-disclaimer"
    OTHER = "other"


class NormalizedMeaning(str, Enum):
    ALLOWED = "allowed"
    DISALLOWED = "disallowed"
    REQUIRED = "required"
    NOT_EVALUATED = "not-evaluated"


class VerificationResult(str, Enum):
    VERIFIED = "verified"
    NOT_FOUND = "not-found"
    AMBIGUOUS = "ambiguous"
    OFFSET_MISMATCH = "offset-mismatch"
    EMPTY_QUOTE = "empty-quote"
    NOT_AUTHENTICATED = "not-authenticated"


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    client_label: str | None = Field(default=None, min_length=1, max_length=200)
    declared_intended_use: IntendedUse


class ProjectRead(ProjectCreate):
    id: UUID
    created_at: datetime


class AssetCreate(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    creator: str | None = Field(default=None, min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=2048)
    declared_license: str = Field(min_length=1, max_length=120)
    supplied_license_text: str | None = Field(default=None, min_length=1, max_length=200_000)
    intended_use: IntendedUse | None = None
    attribution_text: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("source_url")
    @classmethod
    def http_url_only(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from urllib.parse import urlparse

        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must be an absolute http or https URL")
        return value.strip()


class AssetUpdate(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    creator: str | None = Field(default=None, min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=2048)
    declared_license: str | None = Field(default=None, min_length=1, max_length=120)
    supplied_license_text: str | None = Field(default=None, min_length=1, max_length=200_000)
    intended_use: IntendedUse | None = None
    attribution_text: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("source_url")
    @classmethod
    def http_url_only(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from urllib.parse import urlparse

        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must be an absolute http or https URL")
        return value.strip()


class AssetRead(AssetCreate):
    id: UUID
    project_id: UUID
    review_status: ReviewStatus


class ConditionVerificationResult(str, Enum):
    VERIFIED = "verified"
    NOT_FOUND = "not-found"
    AMBIGUOUS = "ambiguous"
    OFFSET_MISMATCH = "offset-mismatch"
    EMPTY_QUOTE = "empty-quote"


class ExtractedConditionRead(ApiModel):
    id: UUID
    asset_id: UUID
    condition_type: ConditionType
    normalized_meaning: NormalizedMeaning | None
    exact_supporting_quotation: str
    quote_start: int | None = Field(default=None, ge=0)
    quote_end: int | None = Field(default=None, ge=0)
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    verification_result: ConditionVerificationResult
    evidence_record_id: UUID


class EvidenceRecordRead(ApiModel):
    id: UUID
    asset_id: UUID
    source_text: str | None
    source_reference: str | None
    quotation: str | None
    verification_status: VerificationResult


class RuleResultRead(ApiModel):
    id: UUID
    asset_id: UUID
    rule_id: str = Field(min_length=1, max_length=80)
    outcome: RuleOutcome
    explanation: str = Field(min_length=1, max_length=500)
    extracted_condition_id: UUID | None
    evidence_record_id: UUID | None


class ExtractionRead(ApiModel):
    asset_id: UUID
    review_status: ReviewStatus
    conditions: list[ExtractedConditionRead]
    evidence: list[EvidenceRecordRead]
    rule_results: list[RuleResultRead]


class ScreeningRead(ApiModel):
    asset_id: UUID
    review_status: ReviewStatus
    rule_results: list[RuleResultRead]


class ReportRead(ApiModel):
    id: UUID
    project_id: UUID
    generated_at: datetime
    included_asset_ids: list[UUID]
    report_version: int = Field(ge=1)
    snapshot: dict
    disclaimer: str
```

`AssetUpdate` uses the same `source_url` check as `AssetCreate`. Omission and JSON null are different: handlers must read `model_fields_set`. A field absent from that set is unchanged. A field present and null clears an optional field. Clearing `declared_license` or `title` is a validation error because those fields cannot become null. `ExtractedConditionRead.verification_result` cannot be `not-authenticated`; that value belongs only on a source-URL evidence row. `evidence_record_id` has no default. A missing or null value fails Pydantic validation. The same-asset, source-text, quotation, and verification checks run before insert and use the error table above.

## Test matrix

These cases define the expected contract. They are not implemented in this phase.

| Case | Input | HTTP | Review status | Required observable |
| --- | --- | --- | --- | --- |
| Normal CC-BY handoff | Project plus asset with title, creator, attribution, `https` source URL, `CC-BY-4.0`, non-empty license text, `noncommercial` use. Extraction returns one verified `license-label` quotation whose single supported label is `CC-BY-4.0`, with `evidence_record_id` pointing at a `source_text` evidence row for that quotation. Confidence `0.99`. | `201` then extraction `200` | `supported-checks-passed` only after that matching verified label | Before extraction the status is `manual-review-required`. The condition's evidence row is `verified` and is not the URL row. The URL evidence row stays `not-authenticated`. Confidence is stored and does not create the status. Declared label is unchanged. |
| Normal CC0 | `CC0-1.0`, license text, URL, `client-delivery-as-is`, null creator and null attribution, then a verified `license-label` quotation whose single supported label is `CC0-1.0` and a matching evidence row | `201` then extraction `200` | `supported-checks-passed` after that matching verified label | Attribution rule passes. Creator stays null. The report includes the limitations notice, including unscreened trademarks, patents, moral rights, and third-party rights. A verified non-label condition alone does not produce this status. |
| Malformed JSON | `POST /api/projects` with `{` | `400` `malformed_json` | No row | No partial project. |
| Missing required field | `{"client_label": "Northwind"}` | `422` `validation_error` | No row | `name` and `declared_intended_use` are named in `details`. |
| Missing license text | Asset JSON omits `supplied_license_text` but includes title and `CC0-1.0` | `201` | `missing-information` | Text stays null. Later `POST .../extractions` returns `409` `missing_source_text` and stores no conditions. |
| Conflicting labels | Declared `CC-BY-4.0`. A verified `license-label` quotation contains only `CC-BY-NC-4.0`, and its evidence row is `verified`. | extraction `200` | `potential-conflict` | Both labels remain. No merged "final license" field. Status is not `supported-checks-passed`. |
| Missing verified license label | Extraction stores only a verified `warranty-disclaimer` condition and its evidence row. No `license-label` condition. | extraction `200` | `manual-review-required` | `quotes-verified` may be `pass`. `declared-vs-extracted-label` is `manual-review-required`. Status is not `supported-checks-passed`. |
| Ambiguous license label | The `license-label` quotation occurs twice in the supplied text, so verification is `ambiguous`, with a matching evidence row. | extraction `200` | `manual-review-required` | Offsets are null. Status is not `supported-checks-passed`. |
| Missing evidence reference | A condition write omits `evidence_record_id` or sends null. | `422` `validation_error` | No new condition | No condition row is stored. |
| Nonexistent evidence record | A condition write uses an `evidence_record_id` that is not in `evidence_records`. | `404` `not_found` | No new condition | No condition row is stored. |
| Conflicting intended use | Project `commercial`, asset `noncommercial`, otherwise complete `CC0-1.0` | `201` | `potential-conflict` | Both uses remain. Asset use is not overwritten. |
| Unsupported variant | `declared_license` is `WTFPL` or `custom` | `201` | `unsupported-license` | Label stored verbatim. No condition is invented to explain it. |
| Invalid URL | `source_url` is `javascript:alert(1)` or `not a url` | `422` `validation_error` | No row | Asset is not created. |
| Missing attribution | `CC-BY-4.0` with null creator and null attribution text, text and URL present | `201` | `missing-information` | `attribution-present` outcome is `missing-information`. |
| Quote absent | Model quotation is not in the supplied text, confidence `0.99` | extraction `200` | `manual-review-required` | Verification is `not-found`. Offsets are null. Status is not `supported-checks-passed`. |
| Unusable model JSON | Ollama returns prose or a schema mismatch | extraction `200` | `manual-review-required` | `conditions` is empty. Rule `extraction-completed` returns `manual-review-required`. |
| NC with commercial delivery | `CC-BY-NC-4.0` and asset use `commercial` | `201` | `potential-conflict` | `nc-vs-declared-use` records the conflict. |
| ND with modification | `CC-BY-ND-4.0` and `client-delivery-modified` | `201` | `potential-conflict` | `nd-vs-declared-use` records the conflict. |
| Client sets status | Asset JSON includes `review_status` | `422` `validation_error` | No row | `extra = forbid` rejects the field. |
| CC-BY-NC-ND blocked | Otherwise field-complete `CC-BY-NC-ND-4.0` with `noncommercial` use and a matching verified `license-label` | extraction `200` | `manual-review-required` | `restrictive-label-not-screened` is `manual-review-required`. Status is not `supported-checks-passed`. |
| ND as-is unclassified | `CC-BY-ND-4.0` with `client-delivery-as-is` and a matching verified `license-label` | extraction `200` | `manual-review-required` | `nd-vs-declared-use` is `manual-review-required`. Status is not `supported-checks-passed`. |
| Evidence asset mismatch | Condition write references an evidence row whose `asset_id` differs | `422` `validation_error` | No new condition | Application-level check rejects the insert. No condition row is stored. |

## Out of scope

- Accounts, teams, and billing.
- Fetching or executing source URLs, downloading assets, OCR, and package-registry scans.
- Asking the model to decide compliance.
- Legal advice, or a status that means the use is lawful.
- Share-alike and all-rights-reserved grants beyond the `manual-review-required` rule above.

## Planned code layout

```
proveniq/
├── frontend/                 Next.js, TypeScript, Tailwind CSS
├── backend/
│   └── app/
│       ├── api/
│       ├── extraction/
│       ├── verification/
│       ├── rules/
│       ├── persistence/
│       └── reports/
└── tests/
```

Backend tests use pytest. Frontend tests use the runner added with the Next.js app. Gemma is called only from `backend/app/extraction`.

## Approved decisions

Assumptions 1–10 are approved with the behavior below.

1. Asset intended use is not copied from the project. When both are set and differ, the status is `potential-conflict`.
2. Asset status precedence is unsupported license, then potential conflict, then missing information, then manual review, then supported checks passed. Every rule result is still returned.
3. `custom`, `unknown`, and any label outside the eight supported labels are `unsupported-license`.
4. `CC-BY-SA-4.0`, `CC-BY-NC-SA-4.0`, and `all-rights-reserved` never reach `supported-checks-passed` in this MVP.
5. A present `http` or `https` URL is required for `supported-checks-passed`, but that URL is always `not-authenticated` and does not block a pass by itself.
6. Offsets are Unicode code points into the stored license text and are set only for a single exact match.
7. Reports include every asset on the project and freeze a JSON snapshot. `report_version` increments per project.
8. The earlier relicense flag and the earlier `permission_declared` field are not part of this contract.
9. `*-NC*` combined with `commercial` or either client-delivery use is `potential-conflict`. `*-ND*` combined with `client-delivery-modified` is `potential-conflict`.
10. Screening runs inside asset create, asset update, and extraction, and can also be called directly.
11. An asset cannot receive `supported-checks-passed` without a matching verified `license-label` quotation. The quotation matches under the whole-label rule, the condition's `verification_result` is `verified`, and `evidence_record_id` points at a valid evidence row for that quotation. A verified condition of any other type is not sufficient. Before that extraction exists, a field-complete asset is `manual-review-required` unless a higher-precedence outcome applies.

These further decisions are also approved:

- Attribution stays the preliminary `attribution-present` check. Its limits are in Screening limitations.
- NonCommercial and NoDerivatives stay the conservative enum screens in assumption 9. `client-delivery-as-is` on an `*-ND*` label is `manual-review-required` because that use cannot be reliably classified as the absence of Adapted Material. A null intended use is not classified; it remains `missing-information`.
- `CC-BY-NC-ND-4.0` cannot receive `supported-checks-passed` in this MVP.
- `CC0-1.0` may pass only when every applicable rule passes, including assumption 11. The report discloses the unscreened rights listed under CC0 in Screening limitations.
