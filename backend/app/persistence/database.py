import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.config import get_settings
from app.schemas import AssetCreate, AssetRead, AssetUpdate, ProjectCreate, ProjectRead, ProjectUpdate, ReviewStatus

PHASE_REVIEW_STATUS = ReviewStatus.MANUAL_REVIEW_REQUIRED


def connect() -> sqlite3.Connection:
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                client_label TEXT,
                declared_intended_use TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                creator TEXT,
                source_url TEXT,
                declared_license TEXT NOT NULL,
                supplied_license_text TEXT,
                intended_use TEXT,
                attribution_text TEXT,
                review_status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS assets_project_id_idx ON assets(project_id);
            """
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_from_row(row: sqlite3.Row) -> ProjectRead:
    return ProjectRead(
        id=UUID(row["id"]),
        name=row["name"],
        client_label=row["client_label"],
        declared_intended_use=row["declared_intended_use"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _asset_from_row(row: sqlite3.Row) -> AssetRead:
    return AssetRead(
        id=UUID(row["id"]),
        project_id=UUID(row["project_id"]),
        title=row["title"],
        creator=row["creator"],
        source_url=row["source_url"],
        declared_license=row["declared_license"],
        supplied_license_text=row["supplied_license_text"],
        intended_use=row["intended_use"],
        attribution_text=row["attribution_text"],
        review_status=row["review_status"],
    )


def create_project(connection: sqlite3.Connection, payload: ProjectCreate) -> ProjectRead:
    project_id = str(uuid4())
    created_at = _utc_now()
    connection.execute(
        """
        INSERT INTO projects (id, name, client_label, declared_intended_use, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, payload.name, payload.client_label, payload.declared_intended_use.value, created_at),
    )
    connection.commit()
    row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _project_from_row(row)


def list_projects(connection: sqlite3.Connection) -> list[ProjectRead]:
    rows = connection.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [_project_from_row(row) for row in rows]


def get_project(connection: sqlite3.Connection, project_id: UUID) -> ProjectRead | None:
    row = connection.execute("SELECT * FROM projects WHERE id = ?", (str(project_id),)).fetchone()
    if row is None:
        return None
    return _project_from_row(row)


def create_asset(connection: sqlite3.Connection, project_id: UUID, payload: AssetCreate) -> AssetRead | None:
    if get_project(connection, project_id) is None:
        return None
    asset_id = str(uuid4())
    created_at = _utc_now()
    connection.execute(
        """
        INSERT INTO assets (
            id, project_id, title, creator, source_url, declared_license,
            supplied_license_text, intended_use, attribution_text, review_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            asset_id,
            str(project_id),
            payload.title,
            payload.creator,
            payload.source_url,
            payload.declared_license,
            payload.supplied_license_text,
            payload.intended_use.value if payload.intended_use else None,
            payload.attribution_text,
            PHASE_REVIEW_STATUS.value,
            created_at,
        ),
    )
    connection.commit()
    row = connection.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    return _asset_from_row(row)


def list_assets(connection: sqlite3.Connection, project_id: UUID) -> list[AssetRead] | None:
    if get_project(connection, project_id) is None:
        return None
    rows = connection.execute(
        "SELECT * FROM assets WHERE project_id = ? ORDER BY created_at ASC",
        (str(project_id),),
    ).fetchall()
    return [_asset_from_row(row) for row in rows]


def get_asset(connection: sqlite3.Connection, asset_id: UUID) -> AssetRead | None:
    row = connection.execute("SELECT * FROM assets WHERE id = ?", (str(asset_id),)).fetchone()
    if row is None:
        return None
    return _asset_from_row(row)


def update_asset(connection: sqlite3.Connection, asset_id: UUID, payload: AssetUpdate) -> AssetRead | None:
    current = connection.execute("SELECT * FROM assets WHERE id = ?", (str(asset_id),)).fetchone()
    if current is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if "intended_use" in changes and changes["intended_use"] is not None:
        changes["intended_use"] = changes["intended_use"].value
    assignments = []
    values: list[object] = []
    for field, value in changes.items():
        assignments.append(f"{field} = ?")
        values.append(value)
    if assignments:
        values.append(str(asset_id))
        connection.execute(
            f"UPDATE assets SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        connection.commit()
    row = connection.execute("SELECT * FROM assets WHERE id = ?", (str(asset_id),)).fetchone()
    return _asset_from_row(row)


def update_project(connection: sqlite3.Connection, project_id: UUID, payload: ProjectUpdate) -> ProjectRead | None:
    current = connection.execute("SELECT * FROM projects WHERE id = ?", (str(project_id),)).fetchone()
    if current is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if "declared_intended_use" in changes and changes["declared_intended_use"] is not None:
        changes["declared_intended_use"] = changes["declared_intended_use"].value
    assignments = []
    values: list[object] = []
    for field, value in changes.items():
        assignments.append(f"{field} = ?")
        values.append(value)
    if assignments:
        values.append(str(project_id))
        connection.execute(f"UPDATE projects SET {', '.join(assignments)} WHERE id = ?", values)
        connection.commit()
    row = connection.execute("SELECT * FROM projects WHERE id = ?", (str(project_id),)).fetchone()
    return _project_from_row(row)


def delete_project(connection: sqlite3.Connection, project_id: UUID) -> bool:
    cursor = connection.execute("DELETE FROM projects WHERE id = ?", (str(project_id),))
    connection.commit()
    return cursor.rowcount == 1


def delete_asset(connection: sqlite3.Connection, asset_id: UUID) -> bool:
    cursor = connection.execute("DELETE FROM assets WHERE id = ?", (str(asset_id),))
    connection.commit()
    return cursor.rowcount == 1


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()
