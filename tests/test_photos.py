"""Tests for the photos API router and StubMediaAdapter.

Uses a dedicated local FastAPI app (not the full create_app()) that includes
ONLY the photos router, backed by the StubMediaAdapter and the same SQLite
test database from conftest.py.

Redis is unavailable in tests — the enqueue step must degrade gracefully.
"""

import io
import itertools

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import auto48.models as _models  # noqa: F401 — register all ORM tables
from auto48.adapters.media.stub import StubMediaAdapter
from auto48.api.routers import photos as photos_router
from auto48.db import Base, async_session_factory, engine  # noqa: F401
from auto48.models.listing import Listing
from auto48.models.photo import Photo
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User
from auto48.models.vehicle import BodyType, Drivetrain, FuelType, Transmission, Vehicle
from auto48.ports.media import MediaPort

_user_counter = itertools.count(1)

# ---------------------------------------------------------------------------
# StubMediaAdapter unit tests (no HTTP layer)
# ---------------------------------------------------------------------------


async def test_stub_put_returns_fake_url():
    adapter = StubMediaAdapter()
    url = await adapter.put("listings/1/abc.jpg", b"fake-image-bytes", "image/jpeg")
    assert url.startswith("http://stub-media/objects/listings/1/abc.jpg")


async def test_stub_url_for():
    adapter = StubMediaAdapter()
    url = adapter.url_for("listings/2/xyz.png")
    assert "xyz.png" in url


async def test_stub_delete():
    adapter = StubMediaAdapter()
    await adapter.put("k", b"data", "image/jpeg")
    await adapter.delete("k")
    # After deletion key must no longer be in the internal store
    assert "k" not in adapter._store


async def test_stub_satisfies_protocol():
    adapter = StubMediaAdapter()
    assert isinstance(adapter, MediaPort)


# ---------------------------------------------------------------------------
# Local FastAPI app fixture (photos-only, stub media, no real Redis)
# ---------------------------------------------------------------------------


def _make_photos_app() -> FastAPI:
    """Build a minimal FastAPI that includes only the photos router.

    Monkey-patches the router's _media_adapter helper to return a shared stub
    so we can inspect calls in tests.
    """
    app = FastAPI()

    # Override the media adapter factory inside the photos router module with a stub
    stub = StubMediaAdapter()
    photos_router._media_adapter = lambda: stub  # type: ignore[attr-defined]

    app.include_router(photos_router.router)
    return app


@pytest.fixture
async def photos_client():
    """ASGI client for the photos-only app, with schema created."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = _make_photos_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def listing_id(photos_client) -> int:  # noqa: ARG001 — ensures schema is created first
    """Insert User + SellerProfile + Vehicle + Listing; return listing.id."""
    async with async_session_factory() as session:
        uid = next(_user_counter)
        user = User(email=f"photo_seller_{uid}@example.com", display_name="Photo Seller")
        session.add(user)
        await session.flush()

        profile = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.flush()

        vehicle = Vehicle(
            make="BMW",
            model="3 Series",
            year=2020,
            fuel=FuelType.PETROL,
            body=BodyType.SEDAN,
            transmission=Transmission.AUTOMATIC,
            drivetrain=Drivetrain.RWD,
        )
        session.add(vehicle)
        await session.flush()

        listing = Listing(
            seller_id=profile.id,
            vehicle_id=vehicle.id,
            title="BMW 3 Series 2020",
            price_eur_cents=2500000,
        )
        session.add(listing)
        await session.flush()
        await session.commit()
        return listing.id


# ---------------------------------------------------------------------------
# HTTP tests via photos_client
# ---------------------------------------------------------------------------


async def test_upload_photo_creates_row(photos_client, listing_id):
    img_bytes = _small_png()
    resp = await photos_client.post(
        f"/v1/listings/{listing_id}/photos",
        files={"file": ("test.png", img_bytes, "image/png")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["listing_id"] == listing_id
    assert body["url"].startswith("http://stub-media")
    assert body["position"] == 1
    assert body["processed"] is False

    # Confirm the DB row exists
    async with async_session_factory() as session:
        photo = await session.scalar(select(Photo).where(Photo.id == body["id"]))
    assert photo is not None
    assert photo.url.startswith("http://stub-media")


async def test_upload_photo_listing_not_found(photos_client):
    img_bytes = _small_png()
    resp = await photos_client.post(
        "/v1/listings/999999/photos",
        files={"file": ("test.png", img_bytes, "image/png")},
    )
    assert resp.status_code == 404


async def test_list_photos(photos_client, listing_id):
    img_bytes = _small_png()
    # Upload two photos
    for _ in range(2):
        await photos_client.post(
            f"/v1/listings/{listing_id}/photos",
            files={"file": ("test.png", img_bytes, "image/png")},
        )

    resp = await photos_client.get(f"/v1/listings/{listing_id}/photos")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 2
    # Positions are ascending
    positions = [i["position"] for i in items]
    assert positions == sorted(positions)


async def test_delete_photo(photos_client, listing_id):
    img_bytes = _small_png()
    upload = await photos_client.post(
        f"/v1/listings/{listing_id}/photos",
        files={"file": ("test.png", img_bytes, "image/png")},
    )
    photo_id = upload.json()["id"]

    del_resp = await photos_client.delete(f"/v1/photos/{photo_id}")
    assert del_resp.status_code == 204

    # Confirm gone from DB
    async with async_session_factory() as session:
        photo = await session.get(Photo, photo_id)
    assert photo is None


async def test_delete_photo_not_found(photos_client):
    resp = await photos_client.delete("/v1/photos/999999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _small_png() -> bytes:
    """Return a minimal valid 1×1 PNG image as bytes."""
    from PIL import Image

    img = Image.new("RGB", (1, 1), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
