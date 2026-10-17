from app.rules.engine import screen_asset


def asset(**overrides):
    body = {
        "declared_license": "CC-BY-4.0",
        "supplied_license_text": "licensed under CC-BY-4.0",
        "source_url": "https://example.com/file",
        "intended_use": "noncommercial",
        "creator": "Ada Lovelace",
        "attribution_text": "Ada Lovelace",
    }
    body.update(overrides)
    return body


def condition(quotation="licensed under CC-BY-4.0", result="verified"):
    return {
        "condition_type": "license-label",
        "verification_result": result,
        "exact_supporting_quotation": quotation,
    }


def test_unknown_license_is_not_a_pass():
    result = screen_asset(asset(declared_license="MIT"), "noncommercial", [condition("licensed under CC-BY-4.0")])
    assert result["review_status"] == "unsupported-license"


def test_commercial_use_of_nc_license_conflicts():
    result = screen_asset(
        asset(declared_license="CC-BY-NC-4.0", intended_use="commercial"),
        "commercial",
        [condition("licensed under CC-BY-NC-4.0")],
    )
    assert result["review_status"] == "potential-conflict"
    assert any(rule["rule_id"] == "nc-vs-declared-use" and rule["outcome"] == "potential-conflict" for rule in result["rule_results"])


def test_matching_verified_cc_by_can_pass():
    result = screen_asset(asset(), "noncommercial", [condition()])
    assert result["review_status"] == "supported-checks-passed"


def test_saved_screening_is_retrieved_without_rerunning(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "screen.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import create_app

    with TestClient(create_app()) as client:
        project = client.post("/api/projects", json={"name": "Job", "declared_intended_use": "noncommercial"}).json()
        asset = client.post(
            f"/api/projects/{project['id']}/assets",
            json={
                "title": "Poster",
                "declared_license": "CC-BY-NC-4.0",
                "intended_use": "commercial",
                "source_url": "https://example.com/poster",
                "supplied_license_text": "licensed under CC-BY-NC-4.0",
                "creator": "Ada",
            },
        ).json()
        missing = client.get(f"/api/assets/{asset['id']}/screening")
        assert missing.status_code == 200
        assert missing.json()["saved"] is False
        assert missing.json()["rule_results"] == []

        first = client.post(f"/api/assets/{asset['id']}/screening")
        assert first.status_code == 200
        assert first.json()["review_status"] == "potential-conflict"
        saved = client.get(f"/api/assets/{asset['id']}/screening")
        assert saved.json()["saved"] is True
        assert saved.json()["outdated"] is False
        assert saved.json()["rule_results"] == first.json()["rule_results"]

        client.patch(f"/api/assets/{asset['id']}", json={"intended_use": "noncommercial"})
        after_edit = client.get(f"/api/assets/{asset['id']}/screening")
        assert after_edit.json()["outdated"] is True
        assert after_edit.json()["review_status"] == "potential-conflict"
        assert after_edit.json()["rule_results"] == first.json()["rule_results"]
    get_settings.cache_clear()


def test_unverified_quote_requires_manual_review():
    result = screen_asset(asset(), "noncommercial", [condition(result="not-found")])
    assert result["review_status"] == "manual-review-required"
