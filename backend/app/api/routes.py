import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from app.persistence.database import (
    create_asset,
    create_project,
    delete_asset,
    delete_project,
    get_asset,
    get_connection,
    get_project,
    list_assets,
    list_projects,
    update_asset,
    update_project,
)
from app.schemas import AssetCreate, AssetRead, AssetUpdate, HealthRead, ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter()


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "not_found", "message": message, "details": []})


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


@router.delete("/api/assets/{asset_id}", status_code=204, tags=["assets"])
def remove_asset(asset_id: UUID, connection: sqlite3.Connection = Depends(get_connection)) -> Response:
    if not delete_asset(connection, asset_id):
        raise not_found("Asset not found.")
    return Response(status_code=204)
