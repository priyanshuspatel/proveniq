import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.extraction.ollama import ModelOutputRejected, OllamaTimeout, OllamaUnavailable, run_extraction
from app.health import inference_status
from app.persistence.database import (
    create_asset,
    create_project,
    delete_asset,
    delete_project,
    get_asset,
    get_connection,
    get_project,
    get_report,
    get_saved_screening,
    list_assets,
    list_conditions,
    list_evidence,
    list_projects,
    list_report_summaries,
    replace_extraction,
    save_screening,
    screening_fingerprint,
    set_review_status,
    update_asset,
    update_project,
)
from app.reports.build import create_project_report
from app.rules.engine import screen_asset
from app.schemas import (
    AnalyzeRead,
    AnalyzeRequest,
    AssetCreate,
    AssetRead,
    AssetUpdate,
    HealthRead,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    ReportCreate,
    ReportRead,
    ReportSummaryRead,
    ReviewStatus,
)

router = APIRouter()


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "not_found", "message": message, "details": []})


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, "details": []})


def validation_error(loc: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "code": "validation_error",
            "message": "The request is invalid.",
            "details": [{"loc": loc, "message": message}],
        },
    )


@router.get("/api/health", response_model=HealthRead, tags=["health"])
def health() -> HealthRead:
    return HealthRead(status="ok")


@router.get("/api/health/live", response_model=HealthRead, tags=["health"])
def health_live() -> HealthRead:
    return HealthRead(status="ok")


@router.get("/api/health/ready", tags=["health"])
def health_ready(connection: sqlite3.Connection = Depends(get_connection)) -> JSONResponse:
    try:
        connection.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return JSONResponse(status_code=503, content={"status": "unavailable", "code": "database_unavailable"})
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.get("/api/health/inference", tags=["health"])
def health_inference() -> JSONResponse:
    body = inference_status(get_settings())
    status_code = 200 if body.get("status") == "ok" else 503
    return JSONResponse(status_code=status_code, content=body)


@router.post("/api/projects", response_model=ProjectRead, status_code=201, tags=["projects"])
def post_project(payload: ProjectCreate, connection: sqlite3.Connection = Depends(get_connection)) -> ProjectRead:
    return create_project(connection, payload)


@router.get("/api/projects", response_model=list[ProjectRead], tags=["projects"])
def get_projects(connection: sqlite3.Connection = Depends(get_connection)) -> list[ProjectRead]:
    return list_projects(connection)


@router.get("/api/projects/{project_id}", response_model=ProjectRead, tags=["projects"])
def get_project_by_id(project_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> ProjectRead:
    project = get_project(connection, project_id)
    if project is None:
        raise not_found("Project not found.")
    return project


@router.patch("/api/projects/{project_id}", response_model=ProjectRead, tags=["projects"])
def patch_project(
    project_id: UUID,
    payload: ProjectUpdate,
    connection: sqlite3.Connection = Depends(get_connection),
) -> ProjectRead:
    if "name" in payload.model_fields_set and payload.name is None:
        raise validation_error("name", "name cannot be cleared")
    if "declared_intended_use" in payload.model_fields_set and payload.declared_intended_use is None:
        raise validation_error("declared_intended_use", "declared_intended_use cannot be cleared")
    project = update_project(connection, project_id, payload)
    if project is None:
        raise not_found("Project not found.")
    return project


@router.delete("/api/projects/{project_id}", status_code=204, tags=["projects"])
def remove_project(project_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> Response:
    if not delete_project(connection, project_id):
        raise not_found("Project not found.")
    return Response(status_code=204)


@router.post(
    "/api/projects/{project_id}/assets",
    response_model=AssetRead,
    status_code=201,
    tags=["assets"],
)
def post_asset(
    project_id: UUID,
    payload: AssetCreate,
    connection: sqlite3.Connection = Depends(get_connection),
) -> AssetRead:
    asset = create_asset(connection, project_id, payload)
    if asset is None:
        raise not_found("Project not found.")
    return asset


@router.get("/api/projects/{project_id}/assets", response_model=list[AssetRead], tags=["assets"])
def get_project_assets(project_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> list[AssetRead]:
    assets = list_assets(connection, project_id)
    if assets is None:
        raise not_found("Project not found.")
    return assets


@router.get("/api/assets/{asset_id}", response_model=AssetRead, tags=["assets"])
def get_asset_by_id(asset_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> AssetRead:
    asset = get_asset(connection, asset_id)
    if asset is None:
        raise not_found("Asset not found.")
    return asset


@router.patch("/api/assets/{asset_id}", response_model=AssetRead, tags=["assets"])
def patch_asset(
    asset_id: UUID,
    payload: AssetUpdate,
    connection: sqlite3.Connection = Depends(get_connection),
) -> AssetRead:
    supplied = payload.model_fields_set
    if "title" in supplied and payload.title is None:
        raise validation_error("title", "title cannot be cleared")
    if "declared_license" in supplied and payload.declared_license is None:
        raise validation_error("declared_license", "declared_license cannot be cleared")
    asset = update_asset(connection, asset_id, payload)
    if asset is None:
        raise not_found("Asset not found.")
    return asset


def _analyze_text(title: str, asset_type: str | None, creator: str | None, source_url: str | None, license_text: str) -> AnalyzeRead:
    try:
        checked = run_extraction(get_settings(), title, asset_type, creator, source_url, license_text)
    except OllamaTimeout as exc:
        raise api_error(504, "extraction_timeout", str(exc)) from exc
    except OllamaUnavailable as exc:
        raise api_error(503, "extraction_unavailable", str(exc)) from exc
    except ModelOutputRejected as exc:
        raise api_error(502, "extraction_invalid_output", str(exc)) from exc
    return AnalyzeRead(
        recognized_license=checked["recognized_license"],
        creator=checked["creator"],
        user_supplied_creator=checked["user_supplied_creator"],
        license_url=checked["license_url"],
        attribution_instructions=checked["attribution_instructions"],
        uncertain_fields=checked["uncertain_fields"],
        evidence=checked["evidence"],
        review_status=ReviewStatus.MANUAL_REVIEW_REQUIRED,
        extraction_note="Extraction is a candidate list. It is not a legal conclusion.",
    )


@router.post("/api/analyze", response_model=AnalyzeRead, tags=["extraction"])
def analyze(payload: AnalyzeRequest) -> AnalyzeRead:
    return _analyze_text(payload.title, payload.asset_type, payload.creator, payload.source_url, payload.license_text)


@router.post("/api/assets/{asset_id}/extractions", response_model=AnalyzeRead, tags=["extraction"])
def extract_asset(
    asset_id: UUID,
    asset_type: str | None = None,
    connection: sqlite3.Connection = Depends(get_connection),
) -> AnalyzeRead:
    asset = get_asset(connection, asset_id)
    if asset is None:
        raise not_found("Asset not found.")
    if not asset.supplied_license_text:
        raise api_error(409, "missing_source_text", "Add license text before extraction. The source URL is not fetched.")
    result = _analyze_text(asset.title, asset_type, asset.creator, asset.source_url, asset.supplied_license_text)
    replace_extraction(
        connection,
        asset_id,
        [item.model_dump() for item in result.evidence],
        asset.supplied_license_text,
        asset.source_url,
    )
    return result


@router.post("/api/assets/{asset_id}/screening", tags=["screening"])
def screen(asset_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> dict:
    asset = get_asset(connection, asset_id)
    if asset is None:
        raise not_found("Asset not found.")
    project = get_project(connection, asset.project_id)
    project_use = project.declared_intended_use.value if project else None
    result = screen_asset(
        asset.model_dump(mode="json"),
        project_use,
        list_conditions(connection, asset_id),
    )
    set_review_status(connection, asset_id, result["review_status"])
    asset_payload = asset.model_dump(mode="json")
    fingerprint = screening_fingerprint(asset_payload, list_conditions(connection, asset_id), project_use)
    save_screening(connection, asset_id, result, fingerprint)
    result["asset_id"] = str(asset_id)
    result["saved"] = True
    result["outdated"] = False
    return result


@router.get("/api/assets/{asset_id}/screening", tags=["screening"])
def saved_screen(asset_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> dict:
    asset = get_asset(connection, asset_id)
    if asset is None:
        raise not_found("Asset not found.")
    project = get_project(connection, asset.project_id)
    project_use = project.declared_intended_use.value if project else None
    fingerprint = screening_fingerprint(asset.model_dump(mode="json"), list_conditions(connection, asset_id), project_use)
    return get_saved_screening(connection, asset_id, fingerprint)


@router.get("/api/assets/{asset_id}/evidence", tags=["extraction"])
def get_evidence(asset_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> list[dict]:
    rows = list_evidence(connection, asset_id)
    if rows is None:
        raise not_found("Asset not found.")
    return rows


@router.post("/api/projects/{project_id}/reports", response_model=ReportRead, status_code=201, tags=["reports"])
def create_report(
    project_id: UUID,
    payload: ReportCreate,
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict:
    report = create_project_report(connection, project_id, payload.asset_types)
    if report is None:
        raise not_found("Project not found.")
    return report


@router.get("/api/projects/{project_id}/reports", response_model=list[ReportSummaryRead], tags=["reports"])
def list_project_reports(
    project_id: UUID,
    connection: sqlite3.Connection = Depends(get_connection),
) -> list[dict]:
    reports = list_report_summaries(connection, project_id)
    if reports is None:
        raise not_found("Project not found.")
    return reports


@router.get("/api/reports/{report_id}", response_model=ReportRead, tags=["reports"])
def read_report(report_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> dict:
    report = get_report(connection, report_id)
    if report is None:
        raise not_found("Report not found.")
    return report


@router.delete("/api/assets/{asset_id}", status_code=204, tags=["assets"])
def remove_asset(asset_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> Response:
    if not delete_asset(connection, asset_id):
        raise not_found("Asset not found.")
    return Response(status_code=204)
