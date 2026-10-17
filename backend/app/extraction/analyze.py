import re

from app.extraction.draft import ExtractionDraft
from app.verification.quotes import label_spans, locate_quote, single_supported_label

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


def analyze_draft(draft: ExtractionDraft, license_text: str, user_creator: str | None, apply_source_spans: bool = True) -> dict:
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

    if apply_source_spans:
        _supplement_license(license_text, evidence_rows, recognized)
        recognized = _recognized_from_evidence(evidence_rows) or recognized
        if recognized != "UNKNOWN":
            uncertain = [field for field in uncertain if field != "recognized_license"]
        _supplement_creator(license_text, evidence_rows, creator, user_creator, uncertain)
        extracted_creator = _creator_from_evidence(evidence_rows, user_creator, uncertain)
        if extracted_creator:
            creator = extracted_creator
        _supplement_attribution(license_text, evidence_rows, attribution)
        attribution = _best_attribution(evidence_rows) or attribution

    if len({label for label, _surface in label_spans(license_text)}) > 1:
        recognized = "UNKNOWN"
        if "recognized_license" not in uncertain:
            uncertain.append("recognized_license")

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


def _append_verified(evidence_rows: list[dict], license_text: str, field: str, quotation: str) -> bool:
    status, start, end = locate_quote(license_text, quotation)
    if status != "verified":
        return False
    if any(row["field"] == field and row["quotation"] == quotation for row in evidence_rows):
        return True
    evidence_rows.append(_row(field, quotation, status, start, end))
    return True


def _recognized_from_evidence(evidence_rows: list[dict]) -> str | None:
    labels = []
    for row in evidence_rows:
        if row["field"] != "license" or row["verification_result"] != "verified":
            continue
        label = single_supported_label(row["quotation"])
        if label:
            labels.append(label)
    unique = set(labels)
    if len(unique) == 1:
        return next(iter(unique))
    return None


def _supplement_license(license_text: str, evidence_rows: list[dict], recognized: str) -> None:
    if recognized != "UNKNOWN" or _recognized_from_evidence(evidence_rows):
        return
    spans = label_spans(license_text)
    labels = {label for label, _surface in spans}
    if len(labels) != 1:
        return
    surfaces = [surface for _label, surface in spans]
    verified_surfaces = [surface for surface in dict.fromkeys(surfaces) if locate_quote(license_text, surface)[0] == "verified"]
    if len(verified_surfaces) != 1:
        return
    _append_verified(evidence_rows, license_text, "license", verified_surfaces[0])


def _creator_from_evidence(evidence_rows: list[dict], user_creator: str | None, uncertain: list[str]) -> str | None:
    names = []
    for row in evidence_rows:
        if row["field"] != "creator" or row["verification_result"] != "verified":
            continue
        match = re.search(r"(?<![A-Za-z])(?:Created by|Photo by|Photograph by|Please credit|Credit) ([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+){0,3})", row["quotation"])
        if match and match.group(1) in row["quotation"]:
            names.append(match.group(1))
    unique = set(names)
    if len(unique) != 1:
        return None
    name = next(iter(unique))
    if user_creator and user_creator != name:
        if "creator" not in uncertain:
            uncertain.append("creator")
        return None
    return name


def _supplement_creator(
    license_text: str,
    evidence_rows: list[dict],
    creator: str | None,
    user_creator: str | None,
    uncertain: list[str],
) -> None:
    if creator:
        return
    pattern = re.compile(r"(?<![A-Za-z])(?:Created by|Photo by|Photograph by|Please credit|Credit) ([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+){0,3})")
    found = []
    for match in pattern.finditer(license_text):
        quotation = match.group(0)
        name = match.group(1)
        if locate_quote(license_text, quotation)[0] == "verified":
            found.append((name, quotation))
    names = {name for name, _quotation in found}
    if len(names) != 1:
        return
    _append_verified(evidence_rows, license_text, "creator", found[0][1])


def _is_attribution_instruction(quotation: str) -> bool:
    return quotation.startswith(("Please credit", "Credit ", "You must give appropriate credit"))


def _best_attribution(evidence_rows: list[dict]) -> str | None:
    instructions = []
    for row in evidence_rows:
        if row["field"] == "attribution" and row["verification_result"] == "verified" and _is_attribution_instruction(row["quotation"]):
            instructions.append(row["quotation"])
    unique = list(dict.fromkeys(instructions))
    if len(unique) == 1:
        return unique[0]
    return None


def _supplement_attribution(license_text: str, evidence_rows: list[dict], attribution: str | None) -> None:
    if _is_attribution_instruction(attribution or "") or _best_attribution(evidence_rows):
        return
    pattern = re.compile(r"(?<![A-Za-z])(?:Please credit [A-Z]|Credit [A-Z]|You must give appropriate credit)[^.]+\.")
    quotations = []
    for match in pattern.finditer(license_text):
        quotation = match.group(0)
        if locate_quote(license_text, quotation)[0] == "verified":
            quotations.append(quotation)
    unique = list(dict.fromkeys(quotations))
    if len(unique) != 1:
        return
    _append_verified(evidence_rows, license_text, "attribution", unique[0])


def _needs_retry(draft: ExtractionDraft, recognized: str, evidence_rows: list[dict]) -> bool:
    if draft.recognized_license != "UNKNOWN" and recognized == "UNKNOWN":
        return True
    return any(row["verification_result"] != "verified" for row in evidence_rows)
