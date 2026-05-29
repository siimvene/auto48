"""Test fixtures: ASGI client backed by a fresh file-based sqlite schema.

A temp file (not :memory:) is used because each async sqlite connection gets its
own in-memory database, which would hide the schema created during lifespan.
"""

import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="auto48-test-")
os.close(_db_fd)
os.environ["AUTO48_ENVIRONMENT"] = "local"
os.environ["AUTO48_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import pytest
from httpx import ASGITransport, AsyncClient

from auto48.db import async_session_factory
from auto48.main import create_app
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


@pytest.fixture
async def seller_id(client) -> int:
    """Insert a User + SellerProfile (after lifespan created the schema); return profile id."""
    async with async_session_factory() as session:
        user = User(email="seller@example.com", display_name="Test Seller")
        session.add(user)
        await session.flush()
        profile = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.flush()
        await session.commit()
        return profile.id


def pytest_sessionfinish(session, exitstatus):
    if os.path.exists(_db_path):
        os.remove(_db_path)
