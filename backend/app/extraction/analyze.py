from app.extraction.draft import ExtractionDraft
from app.verification.quotes import locate_quote, single_supported_label

FIELD_TO_CONDITION = {
    "license": "license-label",
    "creator": "other",
    "license_url": "other",
    "attribution": "attribution-required",
}


def _row(field: str, quotation: str, status: str, start: int | None, end: int | None) -> dict:
    return {
        "field": field,
        "condition_type": FIELD_TO_CONDITION[field],
        "quotation": quotation,
        "verification_result": status,
        "quote_start": start,
        "quote_end": end,
        "confidence": None,
    }


def analyze_draft(draft: ExtractionDraft, license_text: str, user_creator: str | None) -> dict:
    evidence_rows = []
    verified: dict[str, list[dict]] = {key: [] for key in FIELD_TO_CONDITION}
    uncertain: list[str] = []

    pairs = (
        ("license", draft.license_quotation),
        ("creator", draft.creator_quotation),
        ("license_url", draft.license_url_quotation),
        ("attribution", draft.attribution_quotation),
    )
    for field, quotation in pairs:
        if quotation is None or quotation == "":
            continue
        status, start, end = locate_quote(license_text, quotation)
        row = _row(field, quotation, status, start, end)
        evidence_rows.append(row)
        if status == "verified":
            verified[field].append(row)

    labels = []
    for row in verified["license"]:
        label = single_supported_label(row["quotation"])
        if label:
            labels.append(label)
    unique_labels = set(labels)
    recognized = "UNKNOWN"
    if len(unique_labels) == 1 and (draft.recognized_license == "UNKNOWN" or draft.recognized_license in unique_labels):
        recognized = next(iter(unique_labels))
    elif draft.recognized_license != "UNKNOWN" or draft.license_quotation:
        uncertain.append("recognized_license")

    quoted_creator = None
    if draft.creator and any(draft.creator in row["quotation"] for row in verified["creator"]):
        quoted_creator = draft.creator
    creator = None
    if quoted_creator and user_creator and quoted_creator != user_creator:
        uncertain.append("creator")
    elif quoted_creator:
        creator = quoted_creator
    elif draft.creator:
        uncertain.append("creator")

    license_url = None
    if draft.license_url and any(draft.license_url in row["quotation"] for row in verified["license_url"]):
        license_url = draft.license_url
    elif draft.license_url or draft.license_url_quotation:
        uncertain.append("license_url")

    attribution = None
    if draft.attribution_instructions and any(
        draft.attribution_instructions in row["quotation"] for row in verified["attribution"]
    ):
        attribution = draft.attribution_instructions
    elif draft.attribution_instructions or draft.attribution_quotation:
        uncertain.append("attribution_instructions")

    return {
        "recognized_license": recognized,
        "creator": creator,
        "user_supplied_creator": user_creator,
        "license_url": license_url,
        "attribution_instructions": attribution,
        "uncertain_fields": sorted(set(uncertain)),
        "evidence": evidence_rows,
        "needs_retry": _needs_retry(draft, recognized, evidence_rows),
    }


def _needs_retry(draft: ExtractionDraft, recognized: str, evidence_rows: list[dict]) -> bool:
    if draft.recognized_license != "UNKNOWN" and recognized == "UNKNOWN":
        return True
    return any(row["verification_result"] != "verified" for row in evidence_rows)
