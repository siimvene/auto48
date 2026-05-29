"""Tests for the natural-language search service and API router.

Structure:
  Part 1 — unit tests for parse_query (pure, no DB).
  Part 2 — integration tests for GET /v1/search using a private SQLite DB,
            mirroring the pattern in test_search.py.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Temp DB file must exist before any auto48 module imports.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="auto48-nlsearch-test-")
os.close(_db_fd)

os.environ["AUTO48_ENVIRONMENT"] = "local"
os.environ["AUTO48_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import auto48.models  # noqa: F401, E402 – registers all ORM metadata
from auto48.api.routers import nl_search  # noqa: E402
from auto48.db import Base, get_db  # noqa: E402
from auto48.models.listing import Listing, ListingStatus  # noqa: E402
from auto48.models.seller import SellerProfile, SellerType  # noqa: E402
from auto48.models.user import User  # noqa: E402
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle  # noqa: E402
from auto48.services.nl_search import ParsedQuery, parse_query  # noqa: E402

# ── Private engine for isolation ─────────────────────────────────────────────

_engine = create_async_engine(f"sqlite+aiosqlite:///{_db_path}", echo=False)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def _override_get_db() -> object:
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager  # type: ignore[arg-type]
async def _lifespan(app: FastAPI) -> object:  # type: ignore[misc]
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await _engine.dispose()


def _make_nl_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(nl_search.router)
    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture(scope="module")
async def nl_client() -> object:
    app = _make_nl_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


@pytest.fixture(scope="module")
async def seeded(nl_client: object) -> dict[str, int]:  # noqa: ARG001
    """Seed deterministic rows; return label→listing_id.

    Uses a sentinel make ('Tesla') that appears exactly once as ACTIVE.
    The other rows use different makes so isolation is guaranteed.
    """
    async with _session_factory() as session:
        user = User(email="nl-test@example.com", display_name="NL Tester")
        session.add(user)
        await session.flush()
        seller = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(seller)
        await session.flush()
        sid = seller.id

        ids: dict[str, int] = {}

        seed_rows: list[
            tuple[
                str, str, str, int, FuelType, BodyType, Transmission, int, ListingStatus
            ]
        ] = [
            # label, make, model, year, fuel, body, transmission, price_cents, status
            (
                "tesla_active",
                "Tesla",
                "Model 3",
                2022,
                FuelType.ELECTRIC,
                BodyType.SEDAN,
                Transmission.AUTOMATIC,
                3_800_000,
                ListingStatus.ACTIVE,
            ),
            (
                "bmw_diesel",
                "BMW",
                "3 Series",
                2019,
                FuelType.DIESEL,
                BodyType.WAGON,
                Transmission.AUTOMATIC,
                2_500_000,
                ListingStatus.ACTIVE,
            ),
            (
                "toyota_petrol",
                "Toyota",
                "Corolla",
                2015,
                FuelType.PETROL,
                BodyType.SEDAN,
                Transmission.MANUAL,
                900_000,
                ListingStatus.ACTIVE,
            ),
            (
                "tesla_draft",
                "Tesla",
                "Model Y",
                2023,
                FuelType.ELECTRIC,
                BodyType.SUV,
                Transmission.AUTOMATIC,
                4_500_000,
                ListingStatus.DRAFT,  # should NOT appear in nl_search results
            ),
        ]

        for label, make, model, year, fuel, body, transmission, price, lst_status in seed_rows:
            vehicle = Vehicle(
                make=make,
                model=model,
                year=year,
                fuel=fuel,
                body=body,
                transmission=transmission,
            )
            session.add(vehicle)
            await session.flush()
            listing = Listing(
                seller_id=sid,
                vehicle_id=vehicle.id,
                title=f"NL test {label}",
                price_eur_cents=price,
                status=lst_status,
            )
            session.add(listing)
            await session.flush()
            ids[label] = listing.id

        await session.commit()
        return ids


# ═════════════════════════════════════════════════════════════════════════════
# Part 1 — parse_query unit tests
# ═════════════════════════════════════════════════════════════════════════════


def test_parse_diesel_wagon_price_max() -> None:
    """ET phrase: fuel=diesel, body=wagon, price_max=1_000_000 cents."""
    pq: ParsedQuery = parse_query("punane diisel universaal kuni 10000 eurot")
    assert pq.fuel == FuelType.DIESEL
    assert pq.body == BodyType.WAGON
    assert pq.price_max_eur_cents == 1_000_000
    assert pq.price_min_eur_cents is None
    assert pq.year_min is None
    assert pq.year_max is None


def test_parse_bmw_automatic_year_min() -> None:
    """ET phrase: make=BMW, transmission=automatic, year_min=2018."""
    pq = parse_query("BMW automaat alates 2018")
    assert pq.make == "BMW"
    assert pq.transmission == Transmission.AUTOMATIC
    assert pq.year_min == 2018
    assert pq.year_max is None
    assert pq.price_min_eur_cents is None


def test_parse_year_max() -> None:
    """kuni + 4-digit year (no currency) → year_max."""
    pq = parse_query("kuni 2015")
    assert pq.year_max == 2015
    assert pq.price_max_eur_cents is None


def test_parse_price_max_with_currency_overrides_year_range() -> None:
    """kuni + number in year range but with EUR hint → price, not year."""
    pq = parse_query("kuni 2000 eurot")
    assert pq.price_max_eur_cents == 200_000  # 2000 × 100 cents
    assert pq.year_max is None


def test_parse_year_min_bare_four_digit() -> None:
    """A bare 19xx/20xx token with no keyword → year_min."""
    pq = parse_query("Toyota 2018")
    assert pq.year_min == 2018
    assert pq.year_max is None


def test_parse_suv_electric_en() -> None:
    """EN: body=suv, fuel=electric."""
    pq = parse_query("electric SUV under 40000")
    assert pq.fuel == FuelType.ELECTRIC
    assert pq.body == BodyType.SUV
    assert pq.price_max_eur_cents == 4_000_000  # 40000 × 100


def test_parse_price_k_suffix() -> None:
    """'10k' → 10_000 EUR → 1_000_000 cents."""
    pq = parse_query("max 10k")
    assert pq.price_max_eur_cents == 1_000_000


def test_parse_price_space_thousands() -> None:
    """'10 000' with space-separator."""
    pq = parse_query("kuni 10 000 eur")
    assert pq.price_max_eur_cents == 1_000_000


def test_parse_price_min_from() -> None:
    """EN 'from N EUR' → price_min."""
    pq = parse_query("from 5000 eur")
    assert pq.price_min_eur_cents == 500_000


def test_parse_alates_year() -> None:
    """ET 'alates YYYY' where YYYY in year range → year_min (no currency hint)."""
    pq = parse_query("alates 2018")
    assert pq.year_min == 2018
    assert pq.price_min_eur_cents is None


def test_parse_hatchback_manual_petrol_et() -> None:
    """ET keyword mix."""
    pq = parse_query("bensiin luukpära manuaal")
    assert pq.fuel == FuelType.PETROL
    assert pq.body == BodyType.HATCHBACK
    assert pq.transmission == Transmission.MANUAL


def test_parse_plugin_hybrid() -> None:
    """PHEV / plug-in → plugin_hybrid."""
    pq = parse_query("plug-in hybrid SUV")
    assert pq.fuel == FuelType.PLUGIN_HYBRID


def test_parse_skoda() -> None:
    """Skoda (latin spelling) recognised as make."""
    pq = parse_query("Skoda universaal")
    assert pq.make == "Skoda"
    assert pq.body == BodyType.WAGON


def test_parse_no_match_garbage() -> None:
    """Nonsense input → all facets None."""
    pq = parse_query("xxxxyyy zzz 999")
    assert pq.make is None
    assert pq.fuel is None
    assert pq.body is None
    assert pq.transmission is None
    assert pq.year_min is None
    assert pq.price_max_eur_cents is None


def test_parse_empty_string() -> None:
    """Empty string → empty ParsedQuery."""
    pq = parse_query("")
    assert pq == ParsedQuery()


def test_parse_convertible_et() -> None:
    """ET kabriolett → convertible."""
    pq = parse_query("kabriolett Tesla")
    assert pq.body == BodyType.CONVERTIBLE
    assert pq.make == "Tesla"


def test_parse_year_min_uuem_kui() -> None:
    """ET 'uuem kui 2019' → year_min."""
    pq = parse_query("uuem kui 2019")
    assert pq.year_min == 2019


# ═════════════════════════════════════════════════════════════════════════════
# Part 2 — HTTP integration tests
# ═════════════════════════════════════════════════════════════════════════════


async def test_empty_q_returns_400(nl_client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(nl_client, AsyncClient)
    resp = await nl_client.get("/v1/search", params={"q": ""})
    assert resp.status_code == 400


async def test_missing_q_returns_400(nl_client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(nl_client, AsyncClient)
    resp = await nl_client.get("/v1/search")
    assert resp.status_code == 400


async def test_nl_search_tesla_finds_only_active(
    nl_client: object, seeded: dict[str, int]
) -> None:
    """Querying 'Tesla' returns only the ACTIVE Tesla listing, not the draft."""
    from httpx import AsyncClient

    assert isinstance(nl_client, AsyncClient)
    resp = await nl_client.get("/v1/search", params={"q": "Tesla"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    items = body["items"]
    assert len(items) == 1
    assert items[0]["id"] == seeded["tesla_active"]
    assert items[0]["vehicle"]["make"] == "Tesla"


async def test_nl_search_parsed_fields_present(nl_client: object) -> None:
    """Response envelope contains 'parsed', 'items', 'total', 'limit', 'offset'."""
    from httpx import AsyncClient

    assert isinstance(nl_client, AsyncClient)
    resp = await nl_client.get("/v1/search", params={"q": "BMW diisel automaat"})
    assert resp.status_code == 200
    body = resp.json()
    assert "parsed" in body
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    parsed = body["parsed"]
    assert parsed["make"] == "BMW"
    assert parsed["fuel"] == "diesel"
    assert parsed["transmission"] == "automatic"


async def test_nl_search_fuel_filter(nl_client: object) -> None:
    """Searching 'diisel' returns only diesel listings."""
    from httpx import AsyncClient

    assert isinstance(nl_client, AsyncClient)
    resp = await nl_client.get("/v1/search", params={"q": "diisel auto"})
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["vehicle"]["fuel"] == "diesel"


async def test_nl_search_price_max_filters(nl_client: object) -> None:
    """price_max_eur_cents=1_000_000 (10000 eur) should return toyota (900k) only."""
    from httpx import AsyncClient

    assert isinstance(nl_client, AsyncClient)
    resp = await nl_client.get(
        "/v1/search", params={"q": "auto kuni 10000 eurot"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["parsed"]["price_max_eur_cents"] == 1_000_000
    for item in body["items"]:
        assert item["price_eur_cents"] <= 1_000_000


async def test_nl_search_pagination(nl_client: object) -> None:
    """limit/offset respected in response."""
    from httpx import AsyncClient

    assert isinstance(nl_client, AsyncClient)
    resp = await nl_client.get(
        "/v1/search", params={"q": "auto", "limit": 1, "offset": 0}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert len(body["items"]) <= 1


def pytest_sessionfinish(session: object, exitstatus: object) -> None:  # noqa: ARG001
    if os.path.exists(_db_path):
        os.remove(_db_path)
