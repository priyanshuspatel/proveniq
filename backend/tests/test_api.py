from uuid import uuid4

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


def project_payload(**overrides):
    body = {
        "name": "Harbor rebrand",
        "client_label": "Northwind",
        "declared_intended_use": "commercial",
    }
    body.update(overrides)
    return body


def asset_payload(**overrides):
    body = {
        "title": "Wordmark",
        "creator": "A. Okonkwo",
        "source_url": "https://example.com/wordmark",
        "declared_license": "CC-BY-4.0",
        "supplied_license_text": "This work is licensed under CC-BY-4.0.",
        "intended_use": "noncommercial",
        "attribution_text": "Wordmark by A. Okonkwo, CC-BY-4.0.",
    }
    body.update(overrides)
    return body


def test_connection_can_be_used_from_the_request_thread(tmp_path, monkeypatch):
    from threading import Thread

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "threads.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.persistence.database import connect, init_db

    init_db()
    connection = connect()
    errors: list[BaseException] = []

    def read() -> None:
        try:
            connection.execute("SELECT 1").fetchone()
        except BaseException as exc:
            errors.append(exc)

    worker = Thread(target=read)
    worker.start()
    worker.join()
    connection.close()
    get_settings.cache_clear()
    assert errors == []


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_project_crud_and_persistence(client):
    created = client.post("/api/projects", json=project_payload())
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Harbor rebrand"
    assert body["client_label"] == "Northwind"
    assert body["declared_intended_use"] == "commercial"
    project_id = body["id"]

    fetched = client.get(f"/api/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == project_id

    listing = client.get("/api/projects")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [project_id]


def test_project_validation(client):
    missing = client.post("/api/projects", json={"client_label": "Northwind"})
    assert missing.status_code == 422
    assert missing.json()["code"] == "validation_error"
    locations = {item["loc"] for item in missing.json()["details"]}
    assert "name" in locations
    assert "declared_intended_use" in locations

    blank = client.post("/api/projects", json=project_payload(name="   "))
    assert blank.status_code == 422

    malformed = client.post("/api/projects", content="{", headers={"content-type": "application/json"})
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "malformed_json"

    missing_project = client.get(f"/api/projects/{uuid4()}")
    assert missing_project.status_code == 404
    assert missing_project.json()["code"] == "not_found"


def test_asset_crud_does_not_invent_a_pass(client):
    project_id = client.post("/api/projects", json=project_payload()).json()["id"]
    created = client.post(f"/api/projects/{project_id}/assets", json=asset_payload())
    assert created.status_code == 201
    asset = created.json()
    assert asset["project_id"] == project_id
    assert asset["review_status"] == "manual-review-required"
    assert asset["review_status"] != "supported-checks-passed"
    assert asset["declared_license"] == "CC-BY-4.0"

    fetched = client.get(f"/api/assets/{asset['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Wordmark"

    listing = client.get(f"/api/projects/{project_id}/assets")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [asset["id"]]

    patched = client.patch(
        f"/api/assets/{asset['id']}",
        json={"creator": None, "source_url": "https://studio.example/files/wordmark"},
    )
    assert patched.status_code == 200
    assert patched.json()["creator"] is None
    assert patched.json()["source_url"] == "https://studio.example/files/wordmark"
    assert patched.json()["title"] == "Wordmark"
    assert patched.json()["review_status"] == "manual-review-required"


def test_asset_validation(client):
    project_id = client.post("/api/projects", json=project_payload()).json()["id"]

    invalid_url = client.post(
        f"/api/projects/{project_id}/assets",
        json=asset_payload(source_url="javascript:alert(1)"),
    )
    assert invalid_url.status_code == 422
    assert invalid_url.json()["code"] == "validation_error"

    status_field = client.post(
        f"/api/projects/{project_id}/assets",
        json=asset_payload(review_status="supported-checks-passed"),
    )
    assert status_field.status_code == 422

    unknown_project = client.post(f"/api/projects/{uuid4()}/assets", json=asset_payload())
    assert unknown_project.status_code == 404

    created = client.post(f"/api/projects/{project_id}/assets", json=asset_payload()).json()
    cleared_title = client.patch(f"/api/assets/{created['id']}", json={"title": None})
    assert cleared_title.status_code == 422
    assert cleared_title.json()["details"][0]["loc"] == "title"

    omitted = client.patch(f"/api/assets/{created['id']}", json={"attribution_text": "Credit line"})
    assert omitted.status_code == 200
    assert omitted.json()["title"] == "Wordmark"
    assert omitted.json()["attribution_text"] == "Credit line"

    missing_asset = client.get(f"/api/assets/{uuid4()}")
    assert missing_asset.status_code == 404


def test_invalid_intended_use_and_unknown_ids(client):
    bad_use = client.post("/api/projects", json=project_payload(declared_intended_use="royalty-free"))
    assert bad_use.status_code == 422
    assert bad_use.json()["code"] == "validation_error"

    missing_asset = client.delete(f"/api/assets/{uuid4()}")
    assert missing_asset.status_code == 404
    assert missing_asset.json()["code"] == "not_found"

    missing_project = client.delete(f"/api/projects/{uuid4()}")
    assert missing_project.status_code == 404


def test_update_and_delete_persist(client):
    project = client.post("/api/projects", json=project_payload()).json()
    updated = client.patch(
        f"/api/projects/{project['id']}",
        json={"name": "Harbor refresh", "client_label": None},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Harbor refresh"
    assert updated.json()["client_label"] is None
    assert updated.json()["declared_intended_use"] == "commercial"

    asset = client.post(f"/api/projects/{project['id']}/assets", json=asset_payload()).json()
    edited = client.patch(f"/api/assets/{asset['id']}", json={"title": "Updated wordmark"})
    assert edited.status_code == 200
    assert edited.json()["title"] == "Updated wordmark"
    assert edited.json()["review_status"] == "manual-review-required"

    removed_asset = client.delete(f"/api/assets/{asset['id']}")
    assert removed_asset.status_code == 204
    assert client.get(f"/api/assets/{asset['id']}").status_code == 404

    second = client.post(f"/api/projects/{project['id']}/assets", json=asset_payload(title="Poster")).json()
    removed_project = client.delete(f"/api/projects/{project['id']}")
    assert removed_project.status_code == 204
    assert client.get(f"/api/projects/{project['id']}").status_code == 404
    assert client.get(f"/api/assets/{second['id']}").status_code == 404


def test_records_survive_a_new_app_on_the_same_database(tmp_path, monkeypatch):
    database = tmp_path / "persist.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as first:
        created = first.post("/api/projects", json=project_payload())
        assert created.status_code == 201
        project_id = created.json()["id"]
        asset = first.post(f"/api/projects/{project_id}/assets", json=asset_payload())
        assert asset.status_code == 201
        asset_id = asset.json()["id"]
    get_settings.cache_clear()

    with TestClient(create_app()) as second:
        fetched = second.get(f"/api/projects/{project_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Harbor rebrand"
        stored = second.get(f"/api/assets/{asset_id}")
        assert stored.status_code == 200
        assert stored.json()["title"] == "Wordmark"
    get_settings.cache_clear()


def test_optional_asset_fields_stay_null(client):
    project_id = client.post("/api/projects", json=project_payload(client_label="   ")).json()["id"]
    project = client.get(f"/api/projects/{project_id}").json()
    assert project["client_label"] is None

    created = client.post(
        f"/api/projects/{project_id}/assets",
        json=asset_payload(
            creator="  ",
            source_url=None,
            supplied_license_text=None,
            intended_use=None,
            attribution_text=None,
            declared_license="custom",
        ),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["creator"] is None
    assert body["source_url"] is None
    assert body["supplied_license_text"] is None
    assert body["intended_use"] is None
    assert body["attribution_text"] is None
    assert body["declared_license"] == "custom"
    assert body["review_status"] == "manual-review-required"
