"""Bounded demo-release transport and static hosting, outside financial engines."""

import asyncio
import logging
import os
import re
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.research.database import get_engine, postgres_url

logger = logging.getLogger("uvicorn.error")
BODY_LIMIT = 1_048_576


class ReleaseLimits:
    """Fixed process-wide limits: bounded memory, no spoofable IP-key dictionary."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.public_calls: deque[float] = deque()
        self.active = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or os.getenv("PUBLIC_RELEASE_MODE") != "1":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        category = (
            "public"
            if path.startswith("/api/public/") or path == "/api/ready"
            else "private"
            if path.startswith("/api/")
            else "static"
        )
        started = time.monotonic()
        # All public queries share one rolling budget, regardless of supplied IP headers.
        if category == "public":
            while self.public_calls and self.public_calls[0] < started - 60:
                self.public_calls.popleft()
            if len(self.public_calls) >= 120:
                await JSONResponse(
                    {"detail": "Public request limit reached"},
                    status_code=429,
                    headers={"Retry-After": "60", "Cache-Control": "no-store"},
                )(scope, receive, send)
                return
            self.public_calls.append(started)
        if self.active >= 8:
            await JSONResponse(
                {"detail": "Release service is busy"},
                status_code=503,
                headers={"Retry-After": "5", "Cache-Control": "no-store"},
            )(scope, receive, send)
            return
        self.active += 1
        status = 500

        async def safe_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower()
                    not in (b"cache-control", b"x-content-type-options", b"referrer-policy")
                ]
                headers.extend(
                    [
                        (
                            b"cache-control",
                            b"public, max-age=31536000, immutable"
                            if path.startswith("/assets/")
                            else b"no-store",
                        ),
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"x-frame-options", b"DENY"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            # Buffer at most 1 MiB before parsing any API write, including chunked bodies.
            if scope["method"] in ("POST", "PUT", "PATCH"):
                headers = dict(scope.get("headers", []))
                try:
                    declared = int(headers.get(b"content-length", b"0"))
                except ValueError:
                    declared = BODY_LIMIT + 1
                body = bytearray()
                oversized = False
                if declared <= BODY_LIMIT:
                    while True:
                        try:
                            message = await asyncio.wait_for(
                                receive(), timeout=max(0.001, 10 - (time.monotonic() - started))
                            )
                        except TimeoutError:
                            await JSONResponse(
                                {"detail": "Request body timed out"}, status_code=408
                            )(scope, receive, safe_send)
                            return
                        if message["type"] == "http.disconnect":
                            return
                        chunk = message.get("body", b"")
                        if len(body) + len(chunk) > BODY_LIMIT:
                            oversized = True
                            break
                        body.extend(chunk)
                        if not message.get("more_body", False):
                            break
                if declared > BODY_LIMIT or oversized:
                    await JSONResponse(
                        {"detail": "Release request exceeds 1 MiB"}, status_code=413
                    )(scope, receive, safe_send)
                    return
                delivered = False

                async def buffered_receive() -> Message:
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await receive()

                await self.app(scope, buffered_receive, safe_send)
            else:
                await self.app(scope, receive, safe_send)
        finally:
            self.active -= 1
            # No path IDs, query strings, request bodies, headers or credentials in logs.
            logger.info(
                "release_request category=%s status=%d elapsed_ms=%.1f",
                category,
                status,
                (time.monotonic() - started) * 1000,
            )


def frontend_file(public: bool = False) -> Response:
    directory = Path(os.environ.get("FRONTEND_DIST", ""))
    target = directory / "demo/index.html" if public else directory / "index.html"
    if not os.environ.get("FRONTEND_DIST") or not target.is_file():
        raise HTTPException(503, "Release frontend unavailable")
    html = target.read_text(encoding="utf-8")
    if os.getenv("RELEASE_ENVIRONMENT") == "staging":
        html = html.replace(
            "<body>",
            '<body><aside aria-label="Staging environment">'
            "Staging environment · synthetic demonstration; not the production release.</aside>",
        )
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


def install_release(app: FastAPI) -> None:
    app.add_middleware(ReleaseLimits)

    def validate_config() -> None:
        if os.getenv("PUBLIC_RELEASE_MODE") != "1" or not os.getenv("FRONTEND_DIST"):
            return
        postgres_url(os.getenv("DATABASE_URL", ""))
        if len(os.getenv("RESEARCH_API_KEY", "").strip()) < 32:
            raise ValueError("Release requires a server-side owner key")
        origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        if any(not origin.strip().startswith("https://") for origin in origins):
            if os.getenv("RELEASE_ALLOW_LOOPBACK") != "1":
                raise ValueError("Release requires explicit HTTPS origins")
        if os.getenv("ENABLE_DEMO_PREVIEW") == "1":
            raise ValueError("Release must disable the fixed local preview")

    app.add_event_handler("startup", validate_config)

    @app.get("/api/ready")
    def readiness() -> dict[str, str]:
        try:
            with get_engine().connect() as connection:
                head = connection.scalar(text("SELECT version_num FROM alembic_version"))
            if head != "20261014_07":
                raise ValueError("Migrations required")
        except (SQLAlchemyError, ValueError, HTTPException) as exc:
            raise HTTPException(503, "Release database is not ready") from exc
        return {"status": "ready"}

    directory = os.environ.get("FRONTEND_DIST")
    if directory:
        app.mount(
            "/assets", StaticFiles(directory=str(Path(directory) / "assets")), name="release-assets"
        )

        @app.get("/demo", response_model=None)
        @app.get("/demo/{version:path}", response_model=None)
        def public_html(version: str = "") -> Response:
            if version and not re.fullmatch(
                r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}", version
            ):
                raise HTTPException(404, "Public page not found")
            return frontend_file(public=True)
