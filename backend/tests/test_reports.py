from uuid import UUID

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def _project(client: TestClient, **overrides):
    body = {"name": "Handoff", "client_label": "Northwind", "declared_intended_use": "noncommercial"}
    body.update(overrides)
    return client.post("/api/projects", json=body).json()


def _asset(client: TestClient, project_id: str, **overrides):
    body = {
        "title": "Wordmark",
        "creator": "Example Studio",
        "source_url": "https://example.com/wordmark",
        "declared_license": "CC-BY-4.0",
        "supplied_license_text": "This work is licensed under CC-BY-4.0 by Example Studio.",
        "intended_use": "noncommercial",
        "attribution_text": "Example Studio, CC-BY-4.0.",
    }
    body.update(overrides)
    return client.post(f"/api/projects/{project_id}/assets", json=body).json()


def _store_quote(asset_id: str, quotation: str, condition_type: str = "license-label", status: str = "verified"):
    from app.persistence.database import connect, replace_extraction

    with connect() as connection:
        replace_extraction(
            connection,
            UUID(asset_id),
            [
                {
                    "condition_type": condition_type,
                    "quotation": quotation,
                    "verification_result": status,
                    "quote_start": 0,
                    "quote_end": len(quotation),
                    "confidence": None,
                }
            ],
            quotation,
            None,
        )


def test_complete_asset_report_includes_verified_license_url_and_disclaimer(client):
    project = _project(client)
    initial = client.get(f"/api/projects/{project['id']}").json()
    assert initial["asset_count"] == 0
    assert initial["review_status"] is None
    asset = _asset(client, project["id"])
    current = client.get(f"/api/projects/{project['id']}").json()
    assert current["asset_count"] == 1
    assert current["review_status"] == "manual-review-required"
    quote = asset["supplied_license_text"]
    _store_quote(asset["id"], quote)
    screened = client.post(f"/api/assets/{asset['id']}/screening")
    assert screened.status_code == 200
    created = client.post(
        f"/api/projects/{project['id']}/reports",
        json={"asset_types": {asset["id"]: "image"}},
    )
    assert created.status_code == 201
    markdown = created.json()["markdown"]
    assert "This report is a preliminary checklist. It is not legal advice." in markdown
    assert "does not guarantee legal compliance" in markdown
    assert "https://creativecommons.org/licenses/by/4.0/" in markdown
    assert "User-supplied facts" in markdown
    assert "AI-extracted evidence" in markdown
    assert "image" in markdown
    assert "Example Studio" in markdown
    assert "This is not legal approval" in markdown
    assert "legally approved" not in markdown.lower()
    fetched = client.get(f"/api/reports/{created.json()['id']}")
    assert fetched.json()["markdown"] == markdown
    assert fetched.json()["report_version"] == 1
    assert fetched.json()["included_asset_count"] == 1


def test_project_report_history_has_real_summary_fields(client):
    project = _project(client)
    _asset(client, project["id"])
    first = client.post(f"/api/projects/{project['id']}/reports", json={}).json()
    second = client.post(f"/api/projects/{project['id']}/reports", json={}).json()

    history = client.get(f"/api/projects/{project['id']}/reports")
    assert history.status_code == 200
    summaries = history.json()
    assert [item["report_version"] for item in summaries] == [2, 1]
    assert all(item["included_asset_count"] == 1 for item in summaries)
    assert all(item["generated_at"] for item in summaries)
    assert summaries[0]["generated_at"] == second["generated_at"]
    assert summaries[1]["generated_at"] == first["generated_at"]


def test_project_report_history_unknown_project_is_not_found(client):
    missing = client.get("/api/projects/00000000-0000-4000-8000-000000000000/reports")
    assert missing.status_code == 404


def test_missing_fields_are_not_invented(client):
    project = _project(client)
    asset = _asset(
        client,
        project["id"],
        creator=None,
        source_url=None,
        supplied_license_text=None,
        intended_use=None,
        attribution_text=None,
        declared_license="CC-BY-4.0",
    )
    created = client.post(f"/api/projects/{project['id']}/reports", json={})
    assert created.status_code == 201
    markdown = created.json()["markdown"]
    assert "Not supplied." in markdown
    assert "No canonical license URL" in markdown
    assert "https://creativecommons.org/licenses/by/4.0/" not in markdown
    assert "No assessment has been saved" in markdown
    assert "requires manual review" in markdown
    assert asset["title"] in markdown


def test_potential_conflict_explanations_are_included(client):
    project = _project(client, declared_intended_use="noncommercial")
    quote = "This work is licensed under CC-BY-NC-4.0 by Example Studio."
    asset = _asset(
        client,
        project["id"],
        title="Campaign still",
        declared_license="CC-BY-NC-4.0",
        intended_use="commercial",
        supplied_license_text=quote,
        source_url="https://example.com/campaign",
    )
    _store_quote(asset["id"], quote)
    assert client.post(f"/api/assets/{asset['id']}/screening").status_code == 200
    markdown = client.post(f"/api/projects/{project['id']}/reports", json={}).json()["markdown"]
    assert "potential-conflict" in markdown
    assert "NonCommercial" in markdown
    assert "https://creativecommons.org/licenses/by-nc/4.0/" in markdown
    assert "This is not legal approval" in markdown


def test_unknown_license_requires_manual_review_without_a_license_link(client):
    project = _project(client)
    asset = _asset(
        client,
        project["id"],
        title="Sketch",
        declared_license="studio-custom",
        supplied_license_text="Internal studio draft. No standard license is named here.",
        creator=None,
        intended_use="client-delivery-as-is",
    )
    assert client.post(f"/api/assets/{asset['id']}/screening").status_code == 200
    markdown = client.post(f"/api/projects/{project['id']}/reports", json={}).json()["markdown"]
    assert "unsupported-license" in markdown
    assert "requires manual review" in markdown
    assert "No canonical license URL" in markdown
    assert "creativecommons.org" not in markdown
    assert "No evidence quotations are stored" in markdown


def test_user_text_cannot_add_a_markdown_heading(client):
    project = _project(client, name="Safe # name")
    _asset(client, project["id"], title="# Injected\n\n## Owned\n```")
    markdown = client.post(f"/api/projects/{project['id']}/reports", json={}).json()["markdown"]
    outside = []
    fenced = False
    marker = None
    for line in markdown.splitlines():
        if line.endswith(" text") and line[:-5] and set(line[:-5]) == {"`"}:
            fenced = True
            marker = line[:-5]
            continue
        if marker and line == marker:
            fenced = False
            marker = None
            continue
        if not fenced and line.startswith("#"):
            outside.append(line)
    assert outside
    assert all(line.startswith("# Proveniq") or line.startswith("## Asset ") or line.startswith("### ") for line in outside)
    assert "# Injected" in markdown
    assert markdown.count("This report is a preliminary checklist. It is not legal advice.") == 2


def test_later_edits_do_not_change_an_existing_report(client):
    project = _project(client)
    asset = _asset(client, project["id"], title="Original title")
    first = client.post(f"/api/projects/{project['id']}/reports", json={}).json()
    client.patch(f"/api/assets/{asset['id']}", json={"title": "Changed title"})
    second = client.post(f"/api/projects/{project['id']}/reports", json={}).json()
    stored = client.get(f"/api/reports/{first['id']}").json()
    assert "Original title" in stored["markdown"]
    assert "Changed title" not in stored["markdown"]
    assert second["report_version"] == 2
    assert "Changed title" in second["markdown"]


def test_unknown_project_report_is_not_found(client):
    missing = client.post("/api/projects/00000000-0000-4000-8000-000000000000/reports", json={})
    assert missing.status_code == 404
