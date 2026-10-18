from app.rules.engine import screen_asset

from conftest import TEST_ACCESS_TOKEN


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

    with TestClient(create_app(), headers={"Authorization": f"Bearer {TEST_ACCESS_TOKEN}"}) as client:
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


def test_project_use_change_invalidates_asset_screening(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "project-screen.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import create_app

    with TestClient(create_app(), headers={"Authorization": f"Bearer {TEST_ACCESS_TOKEN}"}) as client:
        project = client.post("/api/projects", json={"name": "Job", "declared_intended_use": "commercial"}).json()
        asset = client.post(
            f"/api/projects/{project['id']}/assets",
            json={
                "title": "Poster",
                "declared_license": "CC0-1.0",
                "intended_use": "commercial",
                "source_url": "https://example.com/poster",
                "supplied_license_text": "licensed under CC0-1.0",
            },
        ).json()
        assert client.post(f"/api/assets/{asset['id']}/screening").status_code == 200
        assert client.get(f"/api/assets/{asset['id']}/screening").json()["outdated"] is False

        updated = client.patch(
            f"/api/projects/{project['id']}",
            json={"declared_intended_use": "noncommercial"},
        )
        assert updated.status_code == 200
        assert updated.json()["review_status"] == "manual-review-required"
        saved = client.get(f"/api/assets/{asset['id']}/screening").json()
        assert saved["outdated"] is True
        assert client.get(f"/api/assets/{asset['id']}").json()["review_status"] == "manual-review-required"
    get_settings.cache_clear()


def test_unverified_quote_requires_manual_review():
    result = screen_asset(asset(), "noncommercial", [condition(result="not-found")])
    assert result["review_status"] == "manual-review-required"


def test_regression_cc_by_4_screening_pass_full_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "screen_cc_by.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import create_app
    from tests.test_extraction import FakeResponse, chat

    notice = "This work is licensed under CC BY 4.0 by Example Studio."
    draft_payload = {
        "recognized_license": "CC-BY-4.0",
        "license_quotation": "CC BY 4.0",
        "creator": "Example Studio",
        "creator_quotation": "Example Studio",
        "license_url": None,
        "license_url_quotation": "",
        "attribution_instructions": None,
        "attribution_quotation": "",
    }
    monkeypatch.setattr("app.extraction.ollama.request.urlopen", lambda _req, timeout=0: FakeResponse(chat(draft_payload)))

    with TestClient(create_app(), headers={"Authorization": f"Bearer {TEST_ACCESS_TOKEN}"}) as client:
        project = client.post("/api/projects", json={"name": "CC BY Project", "declared_intended_use": "commercial"}).json()
        asset = client.post(
            f"/api/projects/{project['id']}/assets",
            json={
                "title": "Graphic Asset",
                "declared_license": "CC-BY-4.0",
                "intended_use": "commercial",
                "source_url": "https://example.com/art",
                "supplied_license_text": notice,
                "creator": "Example Studio",
                "attribution_text": "Artwork by Example Studio (CC BY 4.0)",
            },
        ).json()

        # Step 1: Run extraction
        extracted = client.post(f"/api/assets/{asset['id']}/extractions")
        assert extracted.status_code == 200
        assert extracted.json()["recognized_license"] == "CC-BY-4.0"

        # Step 2: Screen asset
        screening = client.post(f"/api/assets/{asset['id']}/screening")
        assert screening.status_code == 200
        data = screening.json()
        assert data["review_status"] == "supported-checks-passed"
        assert data["summary"] == "The recorded checks passed. This is not a legal clearance."

        rules = {rule["rule_id"]: rule for rule in data["rule_results"]}
        assert rules["declared-license-supported"]["outcome"] == "pass"
        assert rules["license-text-present"]["outcome"] == "pass"
        assert rules["attribution-present"]["outcome"] == "pass"
        assert rules["declared-vs-extracted-label"]["outcome"] == "pass"
        assert rules["nc-vs-declared-use"]["outcome"] == "pass"
        assert rules["nd-vs-declared-use"]["outcome"] == "pass"
        assert rules["quotes-verified"]["outcome"] == "pass"
        assert all(rule["outcome"] == "pass" for rule in data["rule_results"])
    get_settings.cache_clear()


def test_regression_unsupported_licenses(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "screen_unsupported.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import create_app

    with TestClient(create_app(), headers={"Authorization": f"Bearer {TEST_ACCESS_TOKEN}"}) as client:
        project = client.post("/api/projects", json={"name": "Unsupported Project", "declared_intended_use": "commercial"}).json()

        for bad_license in ["MIT", "GPL-3.0", "Apache-2.0", "Proprietary"]:
            asset = client.post(
                f"/api/projects/{project['id']}/assets",
                json={
                    "title": f"Code under {bad_license}",
                    "declared_license": bad_license,
                    "intended_use": "commercial",
                    "source_url": "https://example.com/repo",
                    "supplied_license_text": f"Licensed under {bad_license}.",
                    "creator": "Author",
                },
            ).json()

            res = client.post(f"/api/assets/{asset['id']}/screening")
            assert res.status_code == 200
            data = res.json()
            assert data["review_status"] == "unsupported-license"
            rule_map = {r["rule_id"]: r for r in data["rule_results"]}
            assert rule_map["declared-license-supported"]["outcome"] == "unsupported-license"
            assert "outside the set this desk can screen" in data["summary"]
    get_settings.cache_clear()


def test_regression_cc_by_missing_attribution():
    # Asset with CC-BY-4.0 without creator or attribution text, matching commercial use
    missing_attr_asset = asset(creator=None, attribution_text=None, intended_use="commercial")
    result = screen_asset(missing_attr_asset, "commercial", [condition()])
    assert result["review_status"] == "missing-information"
    rule_map = {r["rule_id"]: r for r in result["rule_results"]}
    assert rule_map["attribution-present"]["outcome"] == "missing-information"
