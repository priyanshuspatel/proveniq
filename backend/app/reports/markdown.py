from app.verification.quotes import single_supported_label

DISCLAIMER = (
    "This report is a preliminary checklist. It is not legal advice. "
    "This report organizes declarations and checked quotations. It does not guarantee legal compliance or the right to use these assets. "
    "Attribution screening checks only that a creator or attribution text is present for CC-BY labels. "
    "NonCommercial and NoDerivatives screening compares the declared intended use and does not determine legal NonCommercial purpose or Adapted Material. "
    "ShareAlike, all-rights-reserved, and CC-BY-NC-ND-4.0 stay in manual review in this version. "
    "A CC0 pass covers only the checks in this specification. It does not cover trademarks, patents, moral rights, or rights held by other people. "
    "A source URL was not fetched and does not authenticate the license."
)

CANONICAL_LICENSE_URLS = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC-BY-NC-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "CC-BY-NC-SA-4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "CC-BY-ND-4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
    "CC-BY-NC-ND-4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
}

STATUS_TEXT = {
    "supported-checks-passed": "Recorded checks passed. This is not legal approval, clearance, or permission to use the asset.",
    "potential-conflict": "Potential conflict. The saved explanations disagree. This requires manual review. This is not legal approval.",
    "missing-information": "Missing information. This requires manual review. This is not legal approval.",
    "unsupported-license": "The declared label is outside the screened set. This requires manual review. This is not legal approval.",
    "manual-review-required": "Manual review is required. This is not legal approval.",
}


def fence(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    run = 0
    longest = 0
    for character in text:
        if character == "`":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    marker = "`" * max(3, longest + 1)
    return f"{marker} text\n{text}\n{marker}"


def _supplied(value: str | None) -> str:
    if value is None or not str(value).strip():
        return "Not supplied."
    return fence(str(value))


def _verified_license_label(conditions: list[dict], declared: str) -> str | None:
    matches = []
    for row in conditions:
        if row.get("condition_type") != "license-label":
            continue
        if row.get("verification_result") != "verified":
            continue
        quotation = row.get("exact_supporting_quotation") or ""
        label = single_supported_label(quotation)
        if label:
            matches.append(label)
    if matches == [declared] and declared in CANONICAL_LICENSE_URLS:
        return declared
    return None


def _asset_section(entry: dict, index: int) -> list[str]:
    asset = entry["asset"]
    conditions = entry["conditions"]
    evidence = entry["evidence"]
    screening = entry["screening"]
    lines = [
        f"## Asset {index}",
        "",
        "### User-supplied facts",
        "",
        "These values were entered by the operator. They were not taken from the model.",
        "",
        "- Title:",
        _supplied(asset.get("title")),
        "- Type:",
        _supplied(entry.get("browser_asset_type")),
        "- Type note: A type is recorded in this browser only. It is not extracted from the license text.",
        "- Creator:",
        _supplied(asset.get("creator")),
        "- Source URL:",
        _supplied(asset.get("source_url")),
        "- Source URL note: A source URL is not fetched and does not authenticate a license.",
        "- Declared license identifier:",
        _supplied(asset.get("declared_license")),
        "- Intended use:",
        _supplied(asset.get("intended_use")),
        "- Attribution text:",
        _supplied(asset.get("attribution_text")),
        "- Supplied license text:",
        _supplied(asset.get("supplied_license_text")),
        "",
        "### License link",
        "",
    ]
    verified = _verified_license_label(conditions, asset.get("declared_license") or "")
    if verified:
        lines.append(
            f"Canonical URL for the verified label {verified}: {CANONICAL_LICENSE_URLS[verified]}"
        )
        lines.append("This URL is the public license page for that verified label. It was not fetched.")
    else:
        lines.append(
            "No canonical license URL. A link is included only when the declared identifier is a recognized label and a verified license quotation contains that same label."
        )
    lines.extend(["", "### AI-extracted evidence", ""])
    quotations = [row for row in evidence if row.get("quotation")]
    if not quotations:
        lines.append("No evidence quotations are stored. Missing evidence was not treated as verified.")
    for row in quotations:
        verified_quote = row.get("verification_status") == "verified"
        lines.append("- Associated field:")
        lines.append(_supplied(row.get("condition_type")))
        lines.append("- Verification:")
        lines.append(_supplied(row.get("verification_status")))
        if not verified_quote:
            lines.append("- This quotation is not verified and requires manual review.")
        if row.get("verification_status") in {"ambiguous", "not-found", "offset-mismatch", "empty-quote"}:
            lines.append("- This quotation is unknown or ambiguous and requires manual review.")
        lines.append("- Quotation:")
        lines.append(_supplied(row.get("quotation")))
        lines.append("- Source text:")
        lines.append(_supplied(row.get("source_text")))
        lines.append("")
    url_rows = [row for row in evidence if row.get("verification_status") == "not-authenticated"]
    if url_rows:
        lines.append("A source-URL row is stored as not authenticated. It is not a quotation and not permission.")
        lines.append("")
    lines.extend(["### Assessment", ""])
    if not screening.get("saved"):
        lines.append("No assessment has been saved. This asset requires manual review. This is not legal approval.")
        lines.append("The stored record status is not shown here as a completed assessment.")
    else:
        status = screening.get("review_status")
        lines.append("Saved status:")
        lines.append(_supplied(status))
        lines.append(STATUS_TEXT.get(status, "This asset requires manual review. This is not legal approval."))
        if screening.get("outdated"):
            lines.append(
                "The saved assessment does not match the current fields. It is not a new result and requires manual review."
            )
        lines.append("Summary:")
        lines.append(_supplied(screening.get("summary")))
        lines.append("")
        missing = [rule for rule in screening.get("rule_results", []) if rule.get("outcome") == "missing-information"]
        conflicts = [rule for rule in screening.get("rule_results", []) if rule.get("outcome") == "potential-conflict"]
        review = [rule for rule in screening.get("rule_results", []) if rule.get("outcome") == "manual-review-required"]
        unsupported = [rule for rule in screening.get("rule_results", []) if rule.get("outcome") == "unsupported-license"]
        lines.append("Missing information:")
        lines.append("None recorded." if not missing else "")
        for rule in missing:
            lines.append("-")
            lines.append(_supplied(rule.get("explanation")))
        lines.append("")
        lines.append("Potential conflicts:")
        lines.append("None recorded." if not conflicts else "")
        for rule in conflicts:
            lines.append("-")
            lines.append(_supplied(rule.get("explanation")))
        lines.append("")
        lines.append("Manual review:")
        manual_lines = unsupported + review
        if not manual_lines and status in {"unsupported-license", "manual-review-required", "missing-information", "potential-conflict"}:
            lines.append("- The assessment status itself requires manual review.")
        elif not manual_lines and not screening.get("outdated"):
            lines.append("None recorded beyond the status sentence above.")
        for rule in manual_lines:
            lines.append("-")
            lines.append(_supplied(rule.get("explanation")))
        if screening.get("outdated"):
            lines.append("- The saved assessment is outdated and requires a new explicit assessment.")
    lines.append("")
    return lines


def render_markdown(snapshot: dict) -> str:
    project = snapshot["project"]
    lines = [
        "# Proveniq handoff checklist",
        "",
        DISCLAIMER,
        "",
        "Nothing in this checklist is legal approval.",
        "",
        "### Project",
        "",
        "- Name:",
        _supplied(project.get("name")),
        "- Client label:",
        _supplied(project.get("client_label")),
        "- Declared project use:",
        _supplied(project.get("declared_intended_use")),
        "",
    ]
    assets = snapshot["assets"]
    if not assets:
        lines.append("No assets are included. Nothing was invented to fill the checklist.")
        lines.append("")
    for index, entry in enumerate(assets, start=1):
        lines.extend(_asset_section(entry, index))
    lines.append(DISCLAIMER)
    lines.append("")
    return "\n".join(lines)
