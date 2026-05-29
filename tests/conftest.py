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

from auto48.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


def pytest_sessionfinish(session, exitstatus):
    if os.path.exists(_db_path):
        os.remove(_db_path)
