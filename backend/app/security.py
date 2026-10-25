"""HTTP origin, host and body protections complementing app.auth."""

from collections.abc import Sequence

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 15 MiB per certificate plus room for multipart headers and the title.
MAX_REQUEST_BODY_SIZE = 16 * 1024 * 1024


class BrowserRequestMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: Sequence[str]) -> None:
        self.app = app
        self.allowed_origins = frozenset(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_private(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
            await send(message)

        headers = Headers(scope=scope)
        origins = headers.getlist("origin")
        # CORS alone does not prevent a browser from sending a form POST.
        if (origins and (len(origins) != 1 or origins[0] not in self.allowed_origins)) or (
            not origins and headers.get("sec-fetch-site") == "cross-site"
        ):
            response = JSONResponse(
                status_code=403, content={"detail": "Источник запроса не разрешён"}
            )
            await response(scope, receive, send_private)
            return

        # Reject oversized declared bodies before even bodyless DELETE handlers run.
        lengths = headers.getlist("content-length")
        if lengths:
            try:
                if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdecimal():
                    raise ValueError
                size = int(lengths[0])
            except ValueError:
                response = JSONResponse(
                    status_code=400, content={"detail": "Недопустимый Content-Length"}
                )
                await response(scope, receive, send_private)
                return
            if size > MAX_REQUEST_BODY_SIZE:
                response = JSONResponse(
                    status_code=413, content={"detail": "Размер запроса не должен превышать 16 МБ"}
                )
                await response(scope, receive, send_private)
                return
        await self.app(scope, receive, send_private)
