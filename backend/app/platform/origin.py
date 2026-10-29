"""The cross-site guard: a state-changing `/api/` request must carry the app's own `Origin`."""

from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.platform.errors import ErrorBody, ErrorResponse

GUARDED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
GUARDED_PREFIX = "/api/"
FORBIDDEN_ORIGIN_MESSAGE = "Запрос отклонён"


def origin_of(url: str) -> str:
    """`scheme://host[:port]` of a URL, lower-cased."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower()


class OriginGuardMiddleware:
    """Refuses with 403 `forbidden_origin` when the header is missing or foreign."""

    def __init__(self, app: ASGIApp, app_base_url: str) -> None:
        self._app = app
        self._allowed = origin_of(app_base_url)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._is_refused(scope):
            body = ErrorBody(code="forbidden_origin", message=FORBIDDEN_ORIGIN_MESSAGE)
            payload = ErrorResponse(error=body).model_dump(exclude_none=True)
            await JSONResponse(status_code=403, content=payload)(scope, receive, send)
            return
        await self._app(scope, receive, send)

    def _is_refused(self, scope: Scope) -> bool:
        if scope["method"] not in GUARDED_METHODS or not scope["path"].startswith(GUARDED_PREFIX):
            return False
        for name, value in scope["headers"]:
            if name == b"origin":
                return str(value, "latin-1").lower() != self._allowed
        return True
