"""Live extraction measurement. Not part of the default pytest run.

Run from backend/: .venv/bin/python tests/evaluate_notices.py
Scores are printed from this process. They are not stored as expected results.
"""

import json
from pathlib import Path

from app.config import get_settings
from app.extraction.ollama import run_extraction
from app.verification.quotes import locate_quote

FIXTURE = json.loads(Path(__file__).parent.joinpath("fixtures/license_notices_v1.json").read_text())


def _accepted_quotes_are_in_source(notice: str, evidence: list[dict]) -> bool:
    for row in evidence:
        if row.get("verification_result") != "verified":
            continue
        status, _, _ = locate_quote(notice, row.get("quotation") or "")
        if status != "verified" or (row.get("quotation") or "") not in notice:
            return False
    return True


def main() -> None:
    notices = [item for item in FIXTURE["notices"] if item["text"].strip()]
    rows = []
    for notice in notices:
        try:
            result = run_extraction(get_settings(), notice["id"], None, None, None, notice["text"].strip())
        except Exception as error:
            rows.append({"id": notice["id"], "error": f"{type(error).__name__}: {error}"})
            continue
        recognized = result["recognized_license"]
        attribution = result["attribution_instructions"]
        expected_attribution = notice["expected_attribution"]
        attribution_ok = attribution == expected_attribution or (
            expected_attribution
            and attribution
            and attribution in notice["text"]
            and expected_attribution in attribution
        )
        creator_ok = result["creator"] == notice["expected_creator"] or (
            notice["expected_creator"] is None and result["creator"] is None
        )
        print(notice["id"], flush=True)
        rows.append(
            {
                "id": notice["id"],
                "class": notice["class"],
                "expected_license": notice["expected_recognized_license"],
                "actual_license": recognized,
                "license_ok": recognized == notice["expected_recognized_license"],
                "attribution_ok": attribution_ok,
                "actual_creator": result["creator"],
                "actual_attribution": attribution,
                "creator_ok": creator_ok,
                "creator_invented": bool(result["creator"]) and result["creator"] not in notice["text"],
                "attribution_invented": bool(attribution) and attribution not in notice["text"],
                "quotes_ok": _accepted_quotes_are_in_source(notice["text"], result["evidence"]),
                "evidence": [
                    {"verification_result": item["verification_result"], "quotation": item["quotation"]}
                    for item in result["evidence"]
                ],
            }
        )
    counted = [row for row in rows if "license_ok" in row]
    def rate(key: str) -> str:
        if not counted:
            return "not measured"
        hits = sum(1 for row in counted if row[key])
        return f"{hits}/{len(counted)}"

    print(json.dumps({
        "fixture_version": FIXTURE["version"],
        "notices_scored": len(counted),
        "errors": [row for row in rows if "error" in row],
        "license_identifier": rate("license_ok"),
        "attribution_field": rate("attribution_ok"),
        "creator_field": rate("creator_ok"),
        "verified_quotes_present_in_source": rate("quotes_ok"),
        "license_failures": [row["id"] for row in counted if not row["license_ok"]],
        "attribution_failures": [row["id"] for row in counted if not row["attribution_ok"]],
        "creator_failures": [
            {"id": row["id"], "expected": next(item["expected_creator"] for item in notices if item["id"] == row["id"]), "actual": row["actual_creator"]}
            for row in counted if not row["creator_ok"]
        ],
        "invented_creators": [row["id"] for row in counted if row["creator_invented"]],
        "invented_attributions": [row["id"] for row in counted if row["attribution_invented"]],
        "quote_failures": [row["id"] for row in counted if not row["quotes_ok"]],
    }, indent=2))


if __name__ == "__main__":
    main()
