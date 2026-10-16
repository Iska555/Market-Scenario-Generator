"""Operational bounds and static privacy are exercised through actual ASGI transport."""

import asyncio
import logging
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from src import release


def application() -> FastAPI:
    app = FastAPI()
    release.install_release(app)

    @app.post("/echo")
    async def echo(request: Request) -> dict:
        return {"bytes": len(await request.body())}

    @app.get("/api/public/check")
    def read() -> dict:
        return {"mode": "demo"}

    return app


def test_body_bounds_chunked_cache_and_log_privacy(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("PUBLIC_RELEASE_MODE", "1")
    caplog.set_level(logging.INFO, logger="uvicorn.error")
    with TestClient(application()) as client:
        assert client.post(
            "/echo", content=b"hello", headers={"X-Research-Key": "do-not-log-secret"}
        ).json() == {"bytes": 5}
        response = client.post(
            "/echo", content=b"no", headers={"Content-Length": str(release.BODY_LIMIT + 1)}
        )
        assert response.status_code == 413 and response.headers["cache-control"] == "no-store"
        response = client.post("/echo", content=iter([b"x" * release.BODY_LIMIT, b"y"]))
        assert response.status_code == 413
        assert (
            client.get("/api/public/check?secret=do-not-log-secret").headers["referrer-policy"]
            == "no-referrer"
        )
    assert "do-not-log-secret" not in caplog.text and "category=" in caplog.text


def test_public_budget_is_process_wide_and_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_RELEASE_MODE", "1")
    with TestClient(application()) as client:
        for index in range(120):
            assert (
                client.get("/api/public/check", headers={"X-Forwarded-For": str(index)}).status_code
                == 200
            )
        response = client.get("/api/public/check")
        assert response.status_code == 429 and response.headers["retry-after"] == "60"
        assert client.get("/echo").status_code == 405  # Other request categories stay usable.


def test_static_public_versions_use_synthetic_metadata_and_staging_label(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "demo").mkdir()
    (tmp_path / "index.html").write_text("<html><body>Owner workspace</body></html>")
    (tmp_path / "demo/index.html").write_text(
        '<html><head><meta property="og:description" content="synthetic data"></head>'
        "<body>Demo</body></html>"
    )
    (tmp_path / "assets/app-a.js").write_text("/* public asset */")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    monkeypatch.setenv("PUBLIC_RELEASE_MODE", "1")
    monkeypatch.setenv("RELEASE_ENVIRONMENT", "staging")
    monkeypatch.setenv("RELEASE_ALLOW_LOOPBACK", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test@localhost/isolated")
    monkeypatch.setenv("RESEARCH_API_KEY", "synthetic-operational-test-key-only")
    monkeypatch.delenv("ENABLE_DEMO_PREVIEW", raising=False)
    with TestClient(application()) as client:
        for path in ("/demo", "/demo/", "/demo/079ef599-a949-4d8f-aab3-be5fc5f90c3a"):
            response = client.get(path)
            assert response.status_code == 200 and "og:description" in response.text
            assert (
                "Staging environment" in response.text
                and response.headers["cache-control"] == "no-store"
            )
        assert client.get("/demo/../../.env").status_code == 404
        assert client.get("/demo/private-draft").status_code == 404
        assert "immutable" in client.get("/assets/app-a.js").headers["cache-control"]
    monkeypatch.setenv("ENABLE_DEMO_PREVIEW", "1")
    with pytest.raises(ValueError, match="disable"):
        with TestClient(application()):
            pass


def test_database_readiness_sanitizes_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable():  # type: ignore[no-untyped-def]
        raise ValueError("sensitive-database-host")

    monkeypatch.setattr(release, "get_engine", unavailable)
    with TestClient(application()) as client:
        result = client.get("/api/ready")
        assert result.status_code == 503 and "sensitive" not in result.text


def test_busy_service_fails_fast_and_releases_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_RELEASE_MODE", "1")

    async def run() -> None:
        entered = asyncio.Event()
        finish = asyncio.Event()
        responses = []

        async def inner(scope, receive, send):  # type: ignore[no-untyped-def]
            entered.set()
            await finish.wait()

        async def receive():  # type: ignore[no-untyped-def]
            return {"type": "http.request", "body": b""}

        async def send(message):  # type: ignore[no-untyped-def]
            responses.append(message)

        limited = release.ReleaseLimits(inner)
        scope = {"type": "http", "path": "/api/public/check", "method": "GET"}
        tasks = [asyncio.create_task(limited(scope, receive, send)) for _ in range(8)]
        await entered.wait()
        await asyncio.sleep(0)
        await limited(scope, receive, send)
        assert any(m.get("status") == 503 for m in responses)
        finish.set()
        await asyncio.gather(*tasks)
        assert limited.active == 0

    asyncio.run(run())
