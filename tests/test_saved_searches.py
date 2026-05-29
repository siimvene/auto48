"""Tests for saved-search CRUD endpoints and run_alerts service.

Mounts ONLY the saved-searches router on a local FastAPI app backed by its own
isolated sqlite database — mirrors the pattern in test_search.py.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Temp file must exist before any module-level import that triggers db.py loading.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="auto48-ss-test-")
os.close(_db_fd)

# Force env vars before importing anything that reads them.
os.environ["AUTO48_ENVIRONMENT"] = "local"
os.environ["AUTO48_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import auto48.models  # noqa: F401, E402 — registers all base ORM metadata
import auto48.models.saved_search  # noqa: F401, E402 — registers SavedSearch / Alert
from auto48.api.routers.saved_searches import router as ss_router  # noqa: E402
from auto48.core.security import create_access_token  # noqa: E402
from auto48.db import Base, get_db  # noqa: E402
from auto48.models.listing import Listing, ListingStatus  # noqa: E402
from auto48.models.saved_search import Alert, SavedSearch  # noqa: E402
from auto48.models.seller import SellerProfile, SellerType  # noqa: E402
from auto48.models.user import User  # noqa: E402
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle  # noqa: E402
from auto48.services.saved_search import run_alerts  # noqa: E402

# ── Private engine wired to our temp file ────────────────────────────────────

_engine = create_async_engine(f"sqlite+aiosqlite:///{_db_path}", echo=False)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def _override_get_db():
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def _lifespan(app: FastAPI):
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await _engine.dispose()


def _make_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(ss_router)
    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture(scope="module")
async def client():
    """ASGI client for the saved-searches router (tables created once)."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


# ── Seed helpers ──────────────────────────────────────────────────────────────


async def _make_user(email: str) -> tuple[int, str]:
    """Insert a User and return (user_id, bearer_token)."""
    async with _session_factory() as session:
        user = User(email=email, display_name=email.split("@")[0], is_active=True)
        session.add(user)
        await session.flush()
        uid = user.id
        await session.commit()
    token = create_access_token(sub=str(uid))
    return uid, token


async def _make_listing(
    seller_id: int,
    *,
    make: str = "Toyota",
    model: str = "Corolla",
    year: int = 2020,
    price: int = 1000000,
    status: ListingStatus = ListingStatus.ACTIVE,
) -> int:
    """Seed a Vehicle+Listing; return listing id."""
    async with _session_factory() as session:
        vehicle = Vehicle(
            make=make,
            model=model,
            year=year,
            fuel=FuelType.PETROL,
            body=BodyType.SEDAN,
            transmission=Transmission.MANUAL,
        )
        session.add(vehicle)
        await session.flush()
        listing = Listing(
            seller_id=seller_id,
            vehicle_id=vehicle.id,
            title=f"Test {make} {model}",
            price_eur_cents=price,
            status=status,
        )
        session.add(listing)
        await session.flush()
        lid = listing.id
        await session.commit()
    return lid


async def _make_seller_for_user(user_id: int) -> int:
    """Insert a SellerProfile for an existing user; return profile id."""
    async with _session_factory() as session:
        profile = SellerProfile(user_id=user_id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.flush()
        pid = profile.id
        await session.commit()
    return pid


# ── Endpoint tests ────────────────────────────────────────────────────────────


async def test_create_saved_search_requires_auth(client: AsyncClient) -> None:
    """POST /v1/saved-searches without a token returns 401."""
    resp = await client.post(
        "/v1/saved-searches",
        json={"name": "test", "query": {}},
    )
    assert resp.status_code == 401


async def test_create_saved_search(client: AsyncClient) -> None:
    """Authenticated POST creates a saved search and returns 201."""
    _uid, token = await _make_user("alice_ss@example.com")
    resp = await client.post(
        "/v1/saved-searches",
        json={"name": "My Toyotas", "query": {"make": "Toyota", "year_min": 2015}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "My Toyotas"
    assert body["active"] is True
    assert body["query"]["make"] == "Toyota"
    assert body["query"]["year_min"] == 2015


async def test_list_saved_searches(client: AsyncClient) -> None:
    """GET /v1/saved-searches returns only current user's searches."""
    uid, token = await _make_user("bob_ss@example.com")
    # Create two searches for bob.
    for name in ("Search A", "Search B"):
        await client.post(
            "/v1/saved-searches",
            json={"name": name, "query": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
    # A third user's search — should NOT appear.
    _uid2, token2 = await _make_user("carol_ss@example.com")
    await client.post(
        "/v1/saved-searches",
        json={"name": "Carol's search", "query": {}},
        headers={"Authorization": f"Bearer {token2}"},
    )

    resp = await client.get(
        "/v1/saved-searches",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    names = {s["name"] for s in resp.json()}
    assert "Search A" in names
    assert "Search B" in names
    assert "Carol's search" not in names


async def test_delete_saved_search_owner(client: AsyncClient) -> None:
    """Owner can delete their own saved search."""
    _uid, token = await _make_user("dave_ss@example.com")
    create_resp = await client.post(
        "/v1/saved-searches",
        json={"name": "To delete", "query": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    ss_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"/v1/saved-searches/{ss_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204

    # Confirm it no longer appears in list.
    list_resp = await client.get(
        "/v1/saved-searches",
        headers={"Authorization": f"Bearer {token}"},
    )
    ids = {s["id"] for s in list_resp.json()}
    assert ss_id not in ids


async def test_delete_saved_search_non_owner_returns_403(client: AsyncClient) -> None:
    """Non-owner receives 403 when attempting to delete another user's search."""
    _uid_owner, token_owner = await _make_user("eve_ss@example.com")
    _uid_other, token_other = await _make_user("frank_ss@example.com")

    create_resp = await client.post(
        "/v1/saved-searches",
        json={"name": "Eve's secret search", "query": {}},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    ss_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"/v1/saved-searches/{ss_id}",
        headers={"Authorization": f"Bearer {token_other}"},
    )
    assert del_resp.status_code == 403


async def test_delete_saved_search_not_found(client: AsyncClient) -> None:
    """DELETE on a non-existent id returns 404."""
    _uid, token = await _make_user("ghost_ss@example.com")
    resp = await client.delete(
        "/v1/saved-searches/999999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── run_alerts unit tests ─────────────────────────────────────────────────────


async def test_run_alerts_creates_alert_and_sends_email() -> None:
    """run_alerts finds new matches, creates Alert rows, and emails the owner."""
    from sqlalchemy import select

    from auto48.adapters.notify.stub import StubNotifyAdapter

    stub = StubNotifyAdapter()

    # Seed a user with a saved search for "Toyota" active listings.
    uid, _token = await _make_user("hunter_ss@example.com")
    seller_id = await _make_seller_for_user(uid)
    listing_id = await _make_listing(
        seller_id,
        make="Toyota",
        model="Camry",
        year=2021,
        status=ListingStatus.ACTIVE,
    )

    async with _session_factory() as session:
        ss = SavedSearch(
            user_id=uid,
            name="My Toyota alert",
            query={"make": "Toyota"},
            active=True,
        )
        session.add(ss)
        await session.flush()
        ss_id = ss.id
        await session.commit()

    # Run alerts — should find the Toyota and create one Alert.
    async with _session_factory() as session:
        await run_alerts(session, stub)
        await session.commit()

    # Assert Alert row exists.
    async with _session_factory() as session:
        alerts = list(
            (
                await session.scalars(
                    select(Alert).where(Alert.saved_search_id == ss_id)
                )
            ).all()
        )
    assert len(alerts) == 1
    assert alerts[0].listing_id == listing_id
    assert alerts[0].notified is True

    # Assert email was sent to the owner (other saved searches in the shared db
    # may also produce emails — we only care about the owner's email here).
    owner_emails = [e for e in stub.sent if e.to == "hunter_ss@example.com"]
    assert len(owner_emails) == 1
    sent = owner_emails[0]
    assert "Toyota" in sent.body or "Camry" in sent.body


async def test_run_alerts_no_duplicate_alert() -> None:
    """Running run_alerts twice does not create duplicate alerts."""
    from sqlalchemy import select

    from auto48.adapters.notify.stub import StubNotifyAdapter

    stub = StubNotifyAdapter()

    uid, _token = await _make_user("repeat_ss@example.com")
    seller_id = await _make_seller_for_user(uid)
    await _make_listing(
        seller_id,
        make="Honda",
        model="Civic",
        year=2019,
        status=ListingStatus.ACTIVE,
    )

    async with _session_factory() as session:
        ss = SavedSearch(
            user_id=uid,
            name="Honda alert",
            query={"make": "Honda"},
            active=True,
        )
        session.add(ss)
        await session.flush()
        ss_id = ss.id
        await session.commit()

    # First run — should create 1 alert and 1 email to this owner.
    async with _session_factory() as session:
        await run_alerts(session, stub)
        await session.commit()

    first_run_owner_emails = [e for e in stub.sent if e.to == "repeat_ss@example.com"]
    assert len(first_run_owner_emails) == 1

    stub.clear()

    # Second run — no new listings, so no new alerts or emails for this owner.
    async with _session_factory() as session:
        await run_alerts(session, stub)
        await session.commit()

    async with _session_factory() as session:
        count = len(
            (
                await session.scalars(
                    select(Alert).where(Alert.saved_search_id == ss_id)
                )
            ).all()
        )
    assert count == 1  # still exactly one alert
    second_run_owner_emails = [e for e in stub.sent if e.to == "repeat_ss@example.com"]
    assert len(second_run_owner_emails) == 0  # no second email for this owner


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if os.path.exists(_db_path):
        os.remove(_db_path)
