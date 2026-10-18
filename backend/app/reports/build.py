from uuid import UUID

from app.persistence.database import (
    get_project,
    get_saved_screening,
    insert_report,
    list_assets,
    list_conditions,
    list_evidence,
    screening_fingerprint,
)
from app.reports.markdown import DISCLAIMER, render_markdown


def create_project_report(connection, project_id: UUID, asset_types: dict[UUID, str]) -> dict | None:
    project = get_project(connection, project_id)
    if project is None:
        return None
    assets = list_assets(connection, project_id) or []
    entries = []
    for asset in assets:
        payload = asset.model_dump(mode="json")
        conditions = list_conditions(connection, asset.id)
        evidence = list_evidence(connection, asset.id) or []
        fingerprint = screening_fingerprint(payload, conditions, project.declared_intended_use.value)
        screening = get_saved_screening(connection, asset.id, fingerprint)
        entries.append(
            {
                "asset": payload,
                "browser_asset_type": asset_types.get(asset.id),
                "conditions": conditions,
                "evidence": evidence,
                "screening": screening,
            }
        )
    snapshot = {
        "project": project.model_dump(mode="json"),
        "assets": entries,
        "disclaimer": DISCLAIMER,
    }
    markdown = render_markdown(snapshot)
    return insert_report(
        connection,
        project_id,
        snapshot,
        DISCLAIMER,
        markdown,
        [str(asset.id) for asset in assets],
    )
