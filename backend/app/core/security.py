"""What stands between the public internet and the catalog.

Three concerns, each small enough to read in one sitting:

* `AdminTokenMiddleware` — every request that changes data carries a secret.
  This is enforced by method rather than per route, so a write endpoint added
  later is protected the moment it exists instead of when somebody remembers to
  decorate it.
* `BodySizeLimitMiddleware` — a declared body larger than any real payload is
  refused before it is read.
* `SecurityHeadersMiddleware` — the response headers that tell a browser not to
  sniff types, frame the page, or leak the referrer.
"""

from __future__ import annotations

import hmac
import logging

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)

ADMIN_TOKEN_HEADER = "X-Admin-Token"

# Methods that change data. GET and HEAD read, OPTIONS is the browser asking
# permission to send the real request and is answered by the CORS layer.
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def presented_token(request: Request) -> str | None:
    """The secret this request carries, from either accepted place.

    The dedicated header is what the frontend sends. `Authorization: Bearer` is
    accepted too, because that is what curl, CI and every API client reach for.
    """
    header = request.headers.get(ADMIN_TOKEN_HEADER)
    if header:
        return header.strip()
    authorization = request.headers.get("authorization", "")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    return None


def token_is_valid(presented: str | None, expected: str) -> bool:
    """Compare in constant time, so a wrong guess leaks nothing by its timing."""
    if not presented or not expected:
        return False
    return hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))


def request_is_admin(request: Request, config: Settings | None = None) -> bool:
    """Whether a read should see what only an admin may: drafts, archived records.

    A server with no key configured (development) treats everyone as admin,
    matching the write gate.
    """
    config = config or settings
    if not config.writes_require_a_token:
        return True
    return token_is_valid(presented_token(request), config.admin_token)


class AdminTokenMiddleware:
    """Refuses any data-changing request that does not carry the admin token.

    With no token configured the gate is open, which is only reachable in
    development: `Settings` refuses to load in production without one.
    """

    def __init__(self, app: ASGIApp, config: Settings | None = None) -> None:
        self.app = app
        self._config = config

    @property
    def config(self) -> Settings:
        return self._config or settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        config = self.config
        request = Request(scope)

        if request.method not in UNSAFE_METHODS or not config.writes_require_a_token:
            await self.app(scope, receive, send)
            return

        if token_is_valid(presented_token(request), config.admin_token):
            await self.app(scope, receive, send)
            return

        # Logged without the presented value: a near-miss in the logs is still a
        # secret, and the logs are read by more people than the token is.
        logger.warning(
            "Rejected an unauthenticated %s %s", request.method, request.url.path
        )
        response = JSONResponse(
            status_code=401,
            content={
                "detail": (
                    "This endpoint changes the catalog and needs an admin token. "
                    f"Send it as the {ADMIN_TOKEN_HEADER} header."
                )
            },
            # Names the scheme without inviting a browser password prompt, which
            # a `WWW-Authenticate: Basic` challenge would trigger.
            headers={"WWW-Authenticate": f'Bearer realm="{config.app_name}"'},
        )
        await response(scope, receive, send)


class BodySizeLimitMiddleware:
    """Refuses a request whose declared body is larger than any real payload.

    This reads `Content-Length` only, so it cannot catch a chunked body that
    lies about its size — the reverse proxy enforces the hard ceiling for that
    case. What it does catch is the cheap version of the attack, before the body
    is read into memory.
    """

    def __init__(self, app: ASGIApp, config: Settings | None = None) -> None:
        self.app = app
        self._config = config

    @property
    def config(self) -> Settings:
        return self._config or settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = self.config.max_body_bytes
        declared = Request(scope).headers.get("content-length")
        if declared is not None:
            try:
                length = int(declared)
            except ValueError:
                length = None
            if length is not None and length > limit:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body is larger than {limit} bytes."},
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    """Adds the response headers a browser needs to be told, and drops one.

    The dropped one is `Server`. Naming the server and its version tells an
    attacker which published vulnerabilities to try first and tells a legitimate
    client nothing it uses.
    """

    def __init__(self, app: ASGIApp, config: Settings | None = None) -> None:
        self.app = app
        self._config = config

    @property
    def config(self) -> Settings:
        return self._config or settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        config = self.config
        path = Request(scope).url.path

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] != "http.response.start":
                await send(message)
                return

            headers = MutableHeaders(scope=message)
            headers["X-Content-Type-Options"] = "nosniff"
            headers["X-Frame-Options"] = "DENY"
            headers["Referrer-Policy"] = "no-referrer"
            headers["Cross-Origin-Opener-Policy"] = "same-origin"
            # API replies are data. Nothing in them should ever be loaded as a
            # page, so the policy forbids every source outright. The interactive
            # docs are the exception: they are a page, and they load their own
            # script bundle.
            if not _is_docs_path(path):
                headers["Content-Security-Policy"] = (
                    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
                    "form-action 'none'"
                )
            if config.send_hsts:
                headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains"
                )
            if "server" in headers:
                del headers["server"]
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


def _is_docs_path(path: str) -> bool:
    return path.rstrip("/") in {"/docs", "/redoc", "/docs/oauth2-redirect"}
