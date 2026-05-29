"""Auth endpoint tests: register → login → me happy path + wrong-password 401.

Uses a local FastAPI app that includes ONLY the auth router (does not call
create_app so main.py is never touched). Tables are created via the lifespan
fixture below. The global conftest.py has already set AUTO48_DATABASE_URL to a
temp sqlite file before this module is imported.

Each test registers its own uniquely-named user to avoid unique-email conflicts
across the shared sqlite database file.
"""

from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import auto48.models  # noqa: F401  — registers ORM metadata on Base
from auto48.api.routers.auth import router as auth_router
from auto48.db import Base, engine


@asynccontextmanager
async def _lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Leave teardown to conftest.pytest_sessionfinish (removes the db file).


def _make_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(auth_router)
    return app


@pytest.fixture
async def auth_client():
    app = _make_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload(tag: str) -> dict:
    """Return a register payload with a unique email per test to avoid conflicts."""
    return {
        "email": f"{tag}@example.com",
        "password": "s3cr3tP@ssword",
        "display_name": tag.capitalize(),
        "seller_type": "PRIVATE",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_register_returns_user_and_token(auth_client: AsyncClient) -> None:
    p = _payload("alice_reg")
    resp = await auth_client.post("/v1/auth/register", json=p)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["email"] == p["email"]
    assert body["user"]["display_name"] == p["display_name"]
    assert body["user"]["is_active"] is True
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_returns_token(auth_client: AsyncClient) -> None:
    p = _payload("alice_login")
    # Register first so the user exists.
    await auth_client.post("/v1/auth/register", json=p)

    resp = await auth_client.post(
        "/v1/auth/login",
        json={"email": p["email"], "password": p["password"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_me_returns_current_user(auth_client: AsyncClient) -> None:
    p = _payload("alice_me")
    reg = await auth_client.post("/v1/auth/register", json=p)
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]

    resp = await auth_client.get(
        "/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == p["email"]


async def test_login_wrong_password_returns_401(auth_client: AsyncClient) -> None:
    p = _payload("alice_wrongpw")
    await auth_client.post("/v1/auth/register", json=p)

    resp = await auth_client.post(
        "/v1/auth/login",
        json={"email": p["email"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401, resp.text
