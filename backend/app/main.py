from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.persistence.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Proveniq",
        summary="Project and asset records for a source-linked license handoff.",
        version="0.2.0",
        lifespan=lifespan,
    )
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        if any(error.get("type") in {"json_invalid", "json_type"} for error in errors):
            return JSONResponse(
                status_code=400,
                content={"code": "malformed_json", "message": "Request body is not valid JSON.", "details": []},
            )
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
            details.append({"loc": location or "body", "message": error.get("msg", "Invalid value.")})
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": "The request is invalid.",
                "details": details,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(exc.detail))
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": "error", "message": str(exc.detail), "details": []},
        )

    return app


app = create_app()
