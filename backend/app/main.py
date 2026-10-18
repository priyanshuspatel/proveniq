import logging
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.persistence.database import init_db

logger = logging.getLogger("proveniq.access")
logger.setLevel(logging.INFO)


class RequestTooLarge(Exception):
    pass


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    @staticmethod
    async def _reject(scope, receive, send) -> None:
        response = JSONResponse(
            status_code=413,
            content={
                "code": "request_too_large",
                "message": "Request body exceeds the configured limit.",
                "details": [],
            },
        )
        await response(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self.max_body_bytes <= 0:
            await self.app(scope, receive, send)
            return

        content_length = next(
            (value for key, value in scope.get("headers", []) if key.lower() == b"content-length"),
            None,
        )
        if content_length is not None:
            try:
                if int(content_length) > self.max_body_bytes:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                pass

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLarge:
            await self._reject(scope, receive, send)


class RequestTimeoutMiddleware:
    def __init__(self, app, timeout_seconds: float):
        self.app = app
        self.timeout_seconds = timeout_seconds

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self.timeout_seconds <= 0:
            await self.app(scope, receive, send)
            return
        try:
            await asyncio.wait_for(self.app(scope, receive, send), timeout=self.timeout_seconds)
        except TimeoutError:
            response = JSONResponse(
                status_code=504,
                content={"code": "request_timeout", "message": "The request exceeded the time limit.", "details": []},
            )
            await response(scope, receive, send)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


class AccessLogMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = 500

        async def send_wrapper(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info("%s %s %s %sms", scope.get("method"), scope.get("path"), status, elapsed_ms)


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_runtime()
    app = FastAPI(
        title="Proveniq",
        summary="Project and asset records for a source-linked license handoff.",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Accept"],
    )
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestTimeoutMiddleware, timeout_seconds=settings.request_timeout_seconds)
    app.add_middleware(RequestSizeLimitMiddleware, max_body_bytes=settings.max_request_body_bytes)
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
