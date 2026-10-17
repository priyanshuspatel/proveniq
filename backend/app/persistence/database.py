import json
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

            CREATE TABLE IF NOT EXISTS screening_results (
                asset_id TEXT PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
                review_status TEXT NOT NULL,
                summary TEXT NOT NULL,
                rule_results_json TEXT NOT NULL,
                input_fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence_records (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                source_text TEXT,
                source_reference TEXT,
                quotation TEXT,
                verification_status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                generated_at TEXT NOT NULL,
                report_version INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                disclaimer TEXT NOT NULL,
                markdown TEXT NOT NULL,
                UNIQUE(project_id, report_version)
            );

            CREATE TABLE IF NOT EXISTS report_assets (
                report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
                asset_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                UNIQUE(report_id, asset_id)
            );

            CREATE TABLE IF NOT EXISTS extracted_conditions (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                condition_type TEXT NOT NULL,
                normalized_meaning TEXT,
                exact_supporting_quotation TEXT NOT NULL,
                quote_start INTEGER,
                quote_end INTEGER,
                extraction_confidence REAL,
                verification_result TEXT NOT NULL,
                evidence_record_id TEXT NOT NULL UNIQUE REFERENCES evidence_records(id) ON DELETE RESTRICT
            );
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


def replace_extraction(connection: sqlite3.Connection, asset_id: UUID, rows: list[dict], source_text: str, source_url: str | None) -> None:
    connection.execute("DELETE FROM extracted_conditions WHERE asset_id = ?", (str(asset_id),))
    connection.execute("DELETE FROM evidence_records WHERE asset_id = ?", (str(asset_id),))
    if source_url:
        connection.execute(
            """
            INSERT INTO evidence_records (id, asset_id, source_text, source_reference, quotation, verification_status)
            VALUES (?, ?, NULL, ?, NULL, 'not-authenticated')
            """,
            (str(uuid4()), str(asset_id), source_url),
        )
    for row in rows:
        evidence_id = str(uuid4())
        connection.execute(
            """
            INSERT INTO evidence_records (id, asset_id, source_text, source_reference, quotation, verification_status)
            VALUES (?, ?, ?, NULL, ?, ?)
            """,
            (evidence_id, str(asset_id), source_text, row["quotation"], row["verification_result"]),
        )
        connection.execute(
            """
            INSERT INTO extracted_conditions (
                id, asset_id, condition_type, normalized_meaning, exact_supporting_quotation,
                quote_start, quote_end, extraction_confidence, verification_result, evidence_record_id
            ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                str(asset_id),
                row["condition_type"],
                row["quotation"],
                row["quote_start"],
                row["quote_end"],
                row["confidence"],
                row["verification_result"],
                evidence_id,
            ),
        )
    connection.execute(
        "UPDATE assets SET review_status = ? WHERE id = ?",
        (PHASE_REVIEW_STATUS.value, str(asset_id)),
    )
    connection.commit()


def list_conditions(connection: sqlite3.Connection, asset_id: UUID) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM extracted_conditions WHERE asset_id = ? ORDER BY rowid",
        (str(asset_id),),
    ).fetchall()
    return [dict(row) for row in rows]


def set_review_status(connection: sqlite3.Connection, asset_id: UUID, status: str) -> None:
    connection.execute("UPDATE assets SET review_status = ? WHERE id = ?", (status, str(asset_id)))
    connection.commit()


def list_evidence(connection: sqlite3.Connection, asset_id: UUID) -> list[dict] | None:
    if get_asset(connection, asset_id) is None:
        return None
    rows = connection.execute(
        """
        SELECT evidence_records.id, evidence_records.asset_id, evidence_records.source_text,
               evidence_records.source_reference, evidence_records.quotation,
               evidence_records.verification_status, extracted_conditions.condition_type
        FROM evidence_records
        LEFT JOIN extracted_conditions ON extracted_conditions.evidence_record_id = evidence_records.id
        WHERE evidence_records.asset_id = ?
        ORDER BY evidence_records.rowid
        """,
        (str(asset_id),),
    ).fetchall()
    return [dict(row) for row in rows]


def screening_fingerprint(asset: dict, conditions: list[dict]) -> str:
    payload = {
        "declared_license": asset.get("declared_license"),
        "supplied_license_text": asset.get("supplied_license_text"),
        "source_url": asset.get("source_url"),
        "intended_use": asset.get("intended_use"),
        "creator": asset.get("creator"),
        "attribution_text": asset.get("attribution_text"),
        "conditions": [
            (
                row.get("condition_type"),
                row.get("exact_supporting_quotation"),
                row.get("verification_result"),
            )
            for row in conditions
        ],
    }
    return json.dumps(payload, sort_keys=True)


def save_screening(connection: sqlite3.Connection, asset_id: UUID, result: dict, fingerprint: str) -> None:
    connection.execute(
        """
        INSERT INTO screening_results (asset_id, review_status, summary, rule_results_json, input_fingerprint, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
            review_status = excluded.review_status,
            summary = excluded.summary,
            rule_results_json = excluded.rule_results_json,
            input_fingerprint = excluded.input_fingerprint,
            created_at = excluded.created_at
        """,
        (
            str(asset_id),
            result["review_status"],
            result["summary"],
            json.dumps(result["rule_results"]),
            fingerprint,
            _utc_now(),
        ),
    )
    connection.commit()


def get_saved_screening(connection: sqlite3.Connection, asset_id: UUID, fingerprint: str) -> dict | None:
    if get_asset(connection, asset_id) is None:
        return None
    row = connection.execute(
        "SELECT * FROM screening_results WHERE asset_id = ?",
        (str(asset_id),),
    ).fetchone()
    if row is None:
        return {"asset_id": str(asset_id), "saved": False, "outdated": False, "rule_results": []}
    return {
        "asset_id": str(asset_id),
        "saved": True,
        "outdated": row["input_fingerprint"] != fingerprint,
        "review_status": row["review_status"],
        "summary": row["summary"],
        "rule_results": json.loads(row["rule_results_json"]),
    }


def insert_report(
    connection: sqlite3.Connection,
    project_id: UUID,
    snapshot: dict,
    disclaimer: str,
    markdown: str,
    asset_ids: list[str],
) -> dict:
    report_id = str(uuid4())
    generated_at = _utc_now()
    version_row = connection.execute(
        "SELECT COALESCE(MAX(report_version), 0) + 1 AS next_version FROM reports WHERE project_id = ?",
        (str(project_id),),
    ).fetchone()
    version = int(version_row["next_version"])
    connection.execute(
        """
        INSERT INTO reports (id, project_id, generated_at, report_version, snapshot_json, disclaimer, markdown)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (report_id, str(project_id), generated_at, version, json.dumps(snapshot), disclaimer, markdown),
    )
    for position, asset_id in enumerate(asset_ids):
        connection.execute(
            "INSERT INTO report_assets (report_id, asset_id, position) VALUES (?, ?, ?)",
            (report_id, asset_id, position),
        )
    connection.commit()
    return get_report(connection, UUID(report_id))


def get_report(connection: sqlite3.Connection, report_id: UUID) -> dict | None:
    row = connection.execute("SELECT * FROM reports WHERE id = ?", (str(report_id),)).fetchone()
    if row is None:
        return None
    asset_rows = connection.execute(
        "SELECT asset_id FROM report_assets WHERE report_id = ? ORDER BY position ASC",
        (str(report_id),),
    ).fetchall()
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "generated_at": row["generated_at"],
        "included_asset_ids": [item["asset_id"] for item in asset_rows],
        "report_version": row["report_version"],
        "snapshot": json.loads(row["snapshot_json"]),
        "disclaimer": row["disclaimer"],
        "markdown": row["markdown"],
    }


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()
