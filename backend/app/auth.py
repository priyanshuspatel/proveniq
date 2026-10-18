import hmac

from fastapi.responses import JSONResponse


PUBLIC_API_PATHS = {
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/health/inference",
}


class AccessTokenMiddleware:
    """Require the configured operator token for every non-public API request."""

    def __init__(self, app, access_token: str):
        self.app = app
        self.access_token = access_token

    @staticmethod
    async def _reject(scope, receive, send) -> None:
        response = JSONResponse(
            status_code=401,
            content={
                "code": "authentication_required",
                "message": "A valid access token is required.",
                "details": [],
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)

    @staticmethod
    def _authorization(scope) -> str | None:
        for key, value in scope.get("headers", []):
            if key.lower() == b"authorization":
                return value.decode("latin-1")
        return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # CORS handles preflight validation and response headers outside this middleware.
        is_api_path = path == "/api" or path.startswith("/api/")
        if scope.get("method") == "OPTIONS" or not is_api_path or path in PUBLIC_API_PATHS:
            await self.app(scope, receive, send)
            return

        authorization = self._authorization(scope)
        if authorization is None:
            await self._reject(scope, receive, send)
            return

        scheme, separator, candidate = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not candidate:
            await self._reject(scope, receive, send)
            return

        if not hmac.compare_digest(candidate, self.access_token):
            await self._reject(scope, receive, send)
            return

        await self.app(scope, receive, send)
