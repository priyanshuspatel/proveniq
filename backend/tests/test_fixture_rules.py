import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.extraction.analyze import analyze_draft
from app.extraction.draft import ExtractionDraft
from app.rules.engine import screen_asset
from app.verification.quotes import locate_quote

FIXTURE = json.loads(Path(__file__).parent.joinpath("fixtures/license_notices_v1.json").read_text())
assert FIXTURE["version"] == 1


@pytest.mark.parametrize("case", FIXTURE["rule_cases"], ids=[case["id"] for case in FIXTURE["rule_cases"]])
def test_rule_engine_matches_labelled_outcome(case):
    result = screen_asset(
        {
            "declared_license": case["declared_license"],
            "supplied_license_text": case["license_text"],
            "source_url": case["source_url"],
            "creator": case["creator"],
            "attribution_text": case["attribution_text"],
            "intended_use": case["intended_use"],
        },
        case["project_use"],
        case["conditions"],
    )
    assert result["review_status"] == case["expected_status"]
    for rule_id, outcome in case["expected_rules"].items():
        match = next(rule for rule in result["rule_results"] if rule["rule_id"] == rule_id)
        assert match["outcome"] == outcome
    assert result["review_status"] != "supported-checks-passed" or case["expected_status"] == "supported-checks-passed"
    assert "legal clearance" in result["summary"] or result["review_status"] != "supported-checks-passed"


@pytest.mark.parametrize("notice", FIXTURE["notices"], ids=[notice["id"] for notice in FIXTURE["notices"]])
def test_a_quotation_absent_from_the_notice_is_not_verified(notice):
    status, start, end = locate_quote(notice["text"], "invented quotation that is not in the notice")
    assert status == "not-found"
    assert start is None and end is None


def test_accepted_license_quote_must_occur_once_in_the_source():
    notice = next(item for item in FIXTURE["notices"] if item["id"] == "repeated-token")
    status, _, _ = locate_quote(notice["text"], "CC-BY-4.0")
    assert status == "ambiguous"
    draft = ExtractionDraft(
        recognized_license="CC-BY-4.0",
        license_quotation="CC-BY-4.0",
        creator=None,
        creator_quotation="",
        license_url=None,
        license_url_quotation="",
        attribution_instructions=None,
        attribution_quotation="",
    )
    result = analyze_draft(draft, notice["text"], None)
    assert result["recognized_license"] == "UNKNOWN"
    assert all(row["verification_result"] != "verified" for row in result["evidence"])


def test_schema_rejects_an_unsupported_identifier_and_a_verdict_is_ignored():
    with pytest.raises(ValidationError):
        ExtractionDraft.model_validate(
            {
                "recognized_license": "MIT",
                "license_quotation": "",
                "creator_quotation": "",
                "license_url_quotation": "",
                "attribution_quotation": "",
            }
        )
    draft = ExtractionDraft.model_validate(
        {
            "recognized_license": "UNKNOWN",
            "license_quotation": "",
            "creator_quotation": "",
            "license_url_quotation": "",
            "attribution_quotation": "",
            "legal_verdict": "use is allowed",
        }
    )
    assert not hasattr(draft, "legal_verdict")


def test_fixture_has_the_required_notice_count():
    assert 25 <= len(FIXTURE["notices"]) <= 30


def _empty_draft():
    return ExtractionDraft(
        recognized_license="UNKNOWN",
        license_quotation="",
        creator=None,
        creator_quotation="",
        license_url=None,
        license_url_quotation="",
        attribution_instructions=None,
        attribution_quotation="",
    )


def test_spaced_license_name_is_recognized_only_from_an_exact_span():
    notice = next(item for item in FIXTURE["notices"] if item["id"] == "spaced-by")
    result = analyze_draft(_empty_draft(), notice["text"], None)
    assert result["recognized_license"] == "CC-BY-4.0"
    quote = next(row for row in result["evidence"] if row["field"] == "license")
    assert quote["quotation"] == "CC BY 4.0"
    assert quote["verification_result"] == "verified"
    assert quote["quotation"] in notice["text"]
    longer = analyze_draft(_empty_draft(), "This work is licensed under CC BY-NC 4.0.", None)
    assert longer["recognized_license"] == "CC-BY-NC-4.0"


def test_a_condition_sentence_does_not_become_a_license_identifier():
    for notice_id in ("deed-by-attribution-term", "deed-nc-term", "deed-cc0-waiver", "two-tokens"):
        notice = next(item for item in FIXTURE["notices"] if item["id"] == notice_id)
        result = analyze_draft(_empty_draft(), notice["text"], None)
        assert result["recognized_license"] == "UNKNOWN"


def test_creator_and_attribution_come_from_a_single_source_span():
    notice = next(item for item in FIXTURE["notices"] if item["id"] == "by-attribution-line")
    result = analyze_draft(_empty_draft(), notice["text"], None)
    assert result["creator"] == "Example Studio"
    assert result["user_supplied_creator"] is None
    assert result["attribution_instructions"] == "Please credit Example Studio and link the license."
    for row in result["evidence"]:
        if row["verification_result"] == "verified":
            assert row["quotation"] in notice["text"]


def test_a_bare_name_quote_does_not_replace_the_credit_sentence():
    notice = next(item for item in FIXTURE["notices"] if item["id"] == "by-attribution-line")
    draft = ExtractionDraft(
        recognized_license="CC-BY-4.0",
        license_quotation="Licensed under CC-BY-4.0.",
        creator="Example Studio",
        creator_quotation="Example Studio",
        license_url=None,
        license_url_quotation="",
        attribution_instructions="Example Studio",
        attribution_quotation="Example Studio",
    )
    result = analyze_draft(draft, notice["text"], None)
    assert result["attribution_instructions"] == "Please credit Example Studio and link the license."
    reserved = next(item for item in FIXTURE["notices"] if item["id"] == "arr-token")
    named = analyze_draft(_empty_draft(), reserved["text"], None)
    assert named["creator"] is None


def test_two_license_names_in_one_notice_are_not_reduced_to_one():
    text = "CC BY 4.0 applies. All rights reserved is also printed."
    draft = ExtractionDraft(
        recognized_license="all-rights-reserved",
        license_quotation="All rights reserved is also printed.",
        creator=None,
        creator_quotation="",
        license_url=None,
        license_url_quotation="",
        attribution_instructions=None,
        attribution_quotation="",
    )
    result = analyze_draft(draft, text, None)
    assert result["recognized_license"] == "UNKNOWN"


def test_ambiguous_creator_phrases_stay_unresolved():
    samples = [
        "The nearby Studio keeps the file.",
        "Draft Notice. Do not circulate this file.",
        "Licensed by Northwind Press for internal preview.",
        "The palette was inspired by Mina Cho.",
        "Shot by Mina Cho and retouched by Northwind Press.",
        "Credit cards are not accepted for this download.",
        "Released under CC BY-NC-SA without a version line.",
    ]
    for text in samples:
        result = analyze_draft(_empty_draft(), text, None)
        assert result["creator"] is None, text
        assert result["attribution_instructions"] is None, text
    versionless = analyze_draft(_empty_draft(), samples[-1], None)
    assert versionless["recognized_license"] == "UNKNOWN"


def test_conflicting_user_supplied_creator_is_not_merged():
    result = analyze_draft(_empty_draft(), "Created by Example Studio under CC-BY-4.0.", "Other Person")
    assert result["creator"] is None
    assert result["user_supplied_creator"] == "Other Person"
    assert "creator" in result["uncertain_fields"]
