"""Score model-only output and the model-plus-span pipeline on the held-out set.

Run from backend/: PYTHONPATH=. .venv/bin/python tests/evaluate_heldout.py
"""

import json
from pathlib import Path

from app.config import get_settings
from app.extraction.analyze import analyze_draft
from app.extraction.ollama import build_prompt, request_draft, run_extraction
from app.rules.engine import screen_asset
from app.verification.quotes import SUPPORTED_LABELS, locate_quote

FIXTURE = json.loads(Path(__file__).parent.joinpath("fixtures/license_notices_heldout_v1.json").read_text())


def _attribution_match(predicted: str | None, expected: str | None, source: str) -> bool:
    if expected is None:
        return predicted is None
    return bool(predicted) and predicted in source and expected in predicted


def _creator_match(predicted: str | None, expected: str | None) -> bool:
    return predicted == expected


def _score(rows: list[dict]) -> dict:
    counted = [row for row in rows if "error" not in row]
    n = len(counted)

    def pr(field: str) -> dict:
        tp = fp = fn = 0
        for row in counted:
            predicted = row[field]
            expected = row[f"expected_{field}"]
            if field == "attribution":
                hit = _attribution_match(predicted, expected, row["text"])
            else:
                hit = _creator_match(predicted, expected)
            if predicted is not None and hit:
                tp += 1
            elif predicted is not None and not hit:
                fp += 1
            elif expected is not None and not hit:
                fn += 1
        precision = None if tp + fp == 0 else tp / (tp + fp)
        recall = None if tp + fn == 0 else tp / (tp + fn)
        return {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": precision,
            "recall": recall,
            "precision_denominator": "emitted values (true positives + false positives)",
            "recall_denominator": "labelled non-null values (true positives + false negatives)",
        }

    license_hits = sum(1 for row in counted if row["license"] == row["expected_license"])
    license_fp = sum(1 for row in counted if row["license"] != "UNKNOWN" and row["license"] != row["expected_license"])
    verified = [quote for row in counted for quote in row["verified_quotes"]]
    verified_ok = sum(1 for quote, source in verified if locate_quote(source, quote)[0] == "verified")
    review_counts: dict[str, int] = {}
    for row in counted:
        review_counts[row["review_status"]] = review_counts.get(row["review_status"], 0) + 1
    manual = sum(count for status, count in review_counts.items() if status != "supported-checks-passed")
    return {
        "notices": n,
        "canonical_license_accuracy": None if n == 0 else license_hits / n,
        "canonical_license_accuracy_denominator": "all scored notices, UNKNOWN included as a class",
        "canonical_license_false_positive_rate": None if n == 0 else license_fp / n,
        "canonical_license_false_positive_denominator": "all scored notices; a false positive is a non-UNKNOWN identifier other than the label",
        "creator": pr("creator"),
        "attribution": pr("attribution"),
        "evidence_verification_rate": None if not verified else verified_ok / len(verified),
        "evidence_verification_denominator": "verified evidence rows; each must occur once in its notice",
        "manual_review_rate": None if n == 0 else manual / n,
        "manual_review_denominator": "scored notices whose rule status is not supported-checks-passed, with no user URL or attribution text supplied",
        "review_status_counts": review_counts,
        "failures": [
            {
                "id": row["id"],
                "license": [row["expected_license"], row["license"]],
                "creator": [row["expected_creator"], row["creator"]],
                "attribution": [row["expected_attribution"], row["attribution"]],
            }
            for row in counted
            if row["license"] != row["expected_license"]
            or not _creator_match(row["creator"], row["expected_creator"])
            or not _attribution_match(row["attribution"], row["expected_attribution"], row["text"])
        ],
    }


def _screen(notice: dict, result: dict) -> str:
    declared = notice["expected_recognized_license"]
    if declared not in SUPPORTED_LABELS:
        declared = "unspecified-notice"
    conditions = []
    for row in result["evidence"]:
        if row["verification_result"] == "verified" and row["field"] == "license":
            conditions.append(
                {
                    "condition_type": "license-label",
                    "verification_result": "verified",
                    "exact_supporting_quotation": row["quotation"],
                }
            )
    screened = screen_asset(
        {
            "declared_license": declared,
            "supplied_license_text": notice["text"],
            "source_url": None,
            "creator": None,
            "attribution_text": None,
            "intended_use": "noncommercial",
        },
        "noncommercial",
        conditions,
    )
    return screened["review_status"]


def _row(notice: dict, result: dict) -> dict:
    verified = [
        (row["quotation"], notice["text"])
        for row in result["evidence"]
        if row["verification_result"] == "verified"
    ]
    return {
        "id": notice["id"],
        "text": notice["text"],
        "license": result["recognized_license"],
        "expected_license": notice["expected_recognized_license"],
        "creator": result["creator"],
        "expected_creator": notice["expected_creator"],
        "attribution": result["attribution_instructions"],
        "expected_attribution": notice["expected_attribution"],
        "verified_quotes": verified,
        "review_status": _screen(notice, result),
    }


def main() -> None:
    settings = get_settings()
    model_rows = []
    pipeline_rows = []
    for notice in FIXTURE["notices"]:
        print(notice["id"], flush=True)
        try:
            draft = request_draft(
                settings,
                build_prompt(notice["id"], None, notice["user_supplied_creator"], None, notice["text"]),
            )
        except Exception as error:
            failure = {"id": notice["id"], "error": f"{type(error).__name__}: {error}"}
            model_rows.append(failure)
            pipeline_rows.append(failure)
            continue
        model_only = analyze_draft(draft, notice["text"], notice["user_supplied_creator"], apply_source_spans=False)
        complete = run_extraction(settings, notice["id"], None, notice["user_supplied_creator"], None, notice["text"])
        model_rows.append(_row(notice, model_only))
        pipeline_rows.append(_row(notice, complete))
    print(json.dumps({
        "fixture_version": FIXTURE["version"],
        "model_only": _score(model_rows),
        "model_plus_deterministic_spans": _score(pipeline_rows),
    }, indent=2))


if __name__ == "__main__":
    main()
