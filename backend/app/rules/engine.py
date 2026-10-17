from app.verification.quotes import SUPPORTED_LABELS, single_supported_label

PRECEDENCE = (
    "unsupported-license",
    "potential-conflict",
    "missing-information",
    "manual-review-required",
    "supported-checks-passed",
)

RESTRICTIVE = {"all-rights-reserved", "CC-BY-SA-4.0", "CC-BY-NC-SA-4.0", "CC-BY-NC-ND-4.0"}

SUMMARIES = {
    "supported-checks-passed": "The recorded checks passed. This is not a legal clearance.",
    "potential-conflict": "A retained statement disagrees with another. Both stay visible for a person to review.",
    "missing-information": "A required detail is still blank.",
    "unsupported-license": "This license label is outside the set this desk can screen.",
    "manual-review-required": "A person still needs to review this asset. The checks did not produce a pass.",
}


def _is_nc(label: str) -> bool:
    return "-NC" in label


def _is_nd(label: str) -> bool:
    return "-ND" in label


def _is_by(label: str) -> bool:
    return label.startswith("CC-BY")


def screen_asset(asset: dict, project_use: str | None, conditions: list[dict]) -> dict:
    label = asset.get("declared_license") or ""
    intended = asset.get("intended_use")
    rules: list[dict] = []

    def add(rule_id: str, outcome: str, explanation: str) -> None:
        rules.append({"rule_id": rule_id, "outcome": outcome, "explanation": explanation})

    if label in SUPPORTED_LABELS:
        add("declared-license-supported", "pass", f"{label} is one of the labels this desk can screen.")
    else:
        add("declared-license-supported", "unsupported-license", f"{label or 'A blank label'} is not in the supported set. It is stored as typed and is not interpreted.")

    if asset.get("supplied_license_text"):
        add("license-text-present", "pass", "License text was supplied.")
    else:
        add("license-text-present", "missing-information", "License text is missing. Paste the notice before screening can use it.")

    if asset.get("source_url"):
        add("source-reference-present", "pass", "A source URL was saved. It was not fetched and does not prove the license.")
    else:
        add("source-reference-present", "missing-information", "A source URL is missing.")

    if intended:
        add("intended-use-present", "pass", "An intended use was declared.")
    else:
        add("intended-use-present", "missing-information", "Intended use was not declared, so it was not classified.")

    if not _is_by(label) or asset.get("creator") or asset.get("attribution_text"):
        add("attribution-present", "pass", "Attribution presence was checked. This does not confirm every CC BY attribution element.")
    else:
        add("attribution-present", "missing-information", "This CC BY label has neither a creator nor attribution text.")

    if intended and project_use and intended != project_use:
        add("project-vs-asset-intended-use", "potential-conflict", "The asset's intended use differs from the project's declared use. Both values are kept.")
    else:
        add("project-vs-asset-intended-use", "pass", "The asset use is blank or matches the project use.")

    license_rows = [row for row in conditions if row.get("condition_type") == "license-label"]
    verified_labels = []
    for row in license_rows:
        if row.get("verification_result") == "verified":
            found = single_supported_label(row.get("exact_supporting_quotation") or "")
            if found:
                verified_labels.append(found)
    if not license_rows:
        add("declared-vs-extracted-label", "manual-review-required", "No verified license quotation is stored, so the declared label cannot be checked against the notice.")
    elif any(row.get("verification_result") != "verified" for row in license_rows):
        add("declared-vs-extracted-label", "manual-review-required", "A license quotation was not verified against the supplied text.")
    elif len(set(verified_labels)) > 1:
        add("declared-vs-extracted-label", "manual-review-required", "Verified quotations name more than one license. They were not merged.")
    elif len(verified_labels) == 1 and verified_labels[0] != label:
        add("declared-vs-extracted-label", "potential-conflict", f"The declared label is {label}, and a verified quotation names {verified_labels[0]}. Neither value was overwritten.")
    elif len(verified_labels) == 1 and verified_labels[0] == label:
        add("declared-vs-extracted-label", "pass", f"A verified quotation matches the declared label {label}.")
    else:
        add("declared-vs-extracted-label", "manual-review-required", "A verified quotation did not contain exactly one supported license label.")

    if not _is_nc(label) or intended is None or intended == "noncommercial":
        add("nc-vs-declared-use", "pass", "No NonCommercial conflict was found in the declared use.")
    else:
        add("nc-vs-declared-use", "potential-conflict", "This NonCommercial label is paired with a commercial or client-delivery use. That pairing is a conflict, not a legal ruling.")

    if not _is_nd(label) or intended is None or intended in {"commercial", "noncommercial"}:
        add("nd-vs-declared-use", "pass", "No NoDerivatives conflict was found in the declared use.")
    elif intended == "client-delivery-modified":
        add("nd-vs-declared-use", "potential-conflict", "This NoDerivatives label is paired with a modified client delivery.")
    else:
        add("nd-vs-declared-use", "manual-review-required", "Client delivery as-is does not establish that no adapted material will be shared.")

    add("source-url-not-authentication", "pass", "The source URL was not fetched and does not authenticate the license.")

    if conditions:
        add("extraction-completed", "pass", "An extraction was stored for this asset.")
    else:
        add("extraction-completed", "manual-review-required", "Extraction has not stored any conditions yet.")

    if conditions and all(row.get("verification_result") == "verified" for row in conditions):
        add("quotes-verified", "pass", "Every stored quotation was found in the supplied text.")
    else:
        add("quotes-verified", "manual-review-required", "A stored quotation is missing or was not verified.")

    if label not in RESTRICTIVE:
        add("restrictive-label-not-screened", "pass", "This label is not in the group that always stays in manual review.")
    else:
        add("restrictive-label-not-screened", "manual-review-required", f"{label} stays in manual review in this version. Share-alike and all-rights grants are not fully screened.")

    outcomes = [rule["outcome"] for rule in rules]
    status = "supported-checks-passed"
    for candidate in PRECEDENCE:
        if candidate == "supported-checks-passed":
            break
        if candidate in outcomes:
            status = candidate
            break
    if any(outcome != "pass" for outcome in outcomes):
        if status == "supported-checks-passed":
            status = "manual-review-required"
    return {"review_status": status, "rule_results": rules, "summary": SUMMARIES[status]}
