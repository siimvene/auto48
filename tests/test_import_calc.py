"""Tests for the import-cost calculator service and HTTP endpoints.

Covers:
  - EU vs non-EU customs duty (duty=0 for EU, duty>0 for non-EU).
  - VAT applied correctly (new vehicle, non-EU, VAT-deductible=False vs True).
  - CO₂ and mass components scale with input values.
  - total_landed_eur_cents == sum of all components.
  - GET /v1/import-calculator returns 200 with valid params.
  - GET /v1/import-calculator returns 400 when required params are missing.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auto48.api.routers.import_calculator import router
from auto48.services.import_calc import (
    REG_TAX_BASE_EUR_CENTS,
    REG_TAX_CO2_RATE_EUR_CENTS_PER_G,
    REG_TAX_CO2_THRESHOLD_G_KM,
    REG_TAX_MASS_RATE_EUR_CENTS_PER_KG,
    REG_TAX_MASS_THRESHOLD_KG,
    STATE_FEE_EUR_CENTS,
    VAT_RATE,
    ImportCostBreakdown,
    ImportCostParams,
    compute_import_cost,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _eu_params(**overrides: object) -> ImportCostParams:
    """Build a minimal EU-origin ImportCostParams (Germany, petrol, 2020)."""
    base: dict[str, object] = dict(
        purchase_price_eur_cents=10_000_00,  # 10 000 EUR
        from_country="DE",
        fuel="petrol",
        first_reg_year=2020,
        transport_eur_cents=40_000,  # 400 EUR explicit
        co2_g_km=130.0,
        mass_kg=1500.0,
        is_vat_deductible=False,
    )
    base.update(overrides)
    return ImportCostParams(**base)  # type: ignore[arg-type]


def _non_eu_params(**overrides: object) -> ImportCostParams:
    """Build a minimal non-EU-origin ImportCostParams (Japan, petrol, 2020)."""
    base: dict[str, object] = dict(
        purchase_price_eur_cents=10_000_00,
        from_country="JP",
        fuel="petrol",
        first_reg_year=2020,
        transport_eur_cents=200_000,  # 2 000 EUR explicit
        co2_g_km=130.0,
        mass_kg=1500.0,
        is_vat_deductible=False,
    )
    base.update(overrides)
    return ImportCostParams(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Unit tests: service function
# ---------------------------------------------------------------------------


def test_eu_import_no_customs_duty() -> None:
    """EU-origin vehicles must have zero customs duty."""
    result = compute_import_cost(_eu_params())
    assert result.customs_duty_eur_cents == 0


def test_non_eu_import_has_customs_duty() -> None:
    """Non-EU-origin vehicles must incur ~10 % customs duty on price + transport."""
    params = _non_eu_params()
    result = compute_import_cost(params)
    assert result.customs_duty_eur_cents > 0

    # Verify magnitude: duty = round((price + transport) * 0.10)
    assert params.transport_eur_cents is not None
    dutiable = params.purchase_price_eur_cents + params.transport_eur_cents
    expected_duty = round(dutiable * 0.10)
    assert result.customs_duty_eur_cents == expected_duty


def test_eu_import_customs_duty_is_zero_regardless_of_price() -> None:
    """EU customs duty must be zero for any price."""
    for price in (1_00, 50_000_00, 500_000_00):
        result = compute_import_cost(_eu_params(purchase_price_eur_cents=price))
        assert result.customs_duty_eur_cents == 0, f"Expected 0 duty for price={price}"


def test_non_eu_duty_scales_with_price() -> None:
    """Higher purchase price must yield higher customs duty for non-EU origin."""
    cheap = compute_import_cost(_non_eu_params(purchase_price_eur_cents=5_000_00))
    expensive = compute_import_cost(_non_eu_params(purchase_price_eur_cents=50_000_00))
    assert expensive.customs_duty_eur_cents > cheap.customs_duty_eur_cents


# ---------------------------------------------------------------------------
# VAT tests
# ---------------------------------------------------------------------------


def test_eu_old_vehicle_no_vat_by_default() -> None:
    """EU-origin vehicle registered > 2 years ago → no VAT (non-VAT-deductible buyer)."""
    # first_reg_year=2019 → age=6 (reference 2025) → not new → EU → no VAT
    result = compute_import_cost(_eu_params(first_reg_year=2019))
    assert result.vat_eur_cents == 0


def test_non_eu_import_has_vat() -> None:
    """Non-EU import must incur VAT (regardless of vehicle age)."""
    result = compute_import_cost(_non_eu_params(first_reg_year=2015))
    assert result.vat_eur_cents > 0


def test_vat_deductible_buyer_has_zero_vat() -> None:
    """When is_vat_deductible=True, VAT component must be zero."""
    result_eu = compute_import_cost(_eu_params(is_vat_deductible=True, first_reg_year=2024))
    assert result_eu.vat_eur_cents == 0

    result_non_eu = compute_import_cost(_non_eu_params(is_vat_deductible=True))
    assert result_non_eu.vat_eur_cents == 0


def test_new_eu_vehicle_attracts_vat() -> None:
    """EU-origin vehicle with first_reg_year=2024 (≤2 years old) must attract VAT."""
    result = compute_import_cost(_eu_params(first_reg_year=2024))
    assert result.vat_eur_cents > 0


def test_vat_rate_is_22_percent() -> None:
    """VAT must equal 22 % of (price + transport + duty), rounded to int cents."""
    params = _non_eu_params()
    result = compute_import_cost(params)
    assert params.transport_eur_cents is not None
    vat_base = (
        params.purchase_price_eur_cents
        + params.transport_eur_cents
        + result.customs_duty_eur_cents
    )
    expected_vat = round(vat_base * VAT_RATE)
    assert result.vat_eur_cents == expected_vat


# ---------------------------------------------------------------------------
# Registration-tax component tests
# ---------------------------------------------------------------------------


def test_registration_tax_base_always_present() -> None:
    """Registration tax must always include at least the base fee."""
    result = compute_import_cost(_eu_params(co2_g_km=0.0, mass_kg=0.0))
    assert result.registration_tax_eur_cents >= REG_TAX_BASE_EUR_CENTS


def test_co2_component_scales() -> None:
    """Higher CO₂ must produce a larger registration tax than lower CO₂."""
    low_co2 = compute_import_cost(_eu_params(co2_g_km=50.0))
    high_co2 = compute_import_cost(_eu_params(co2_g_km=250.0))
    assert high_co2.registration_tax_eur_cents > low_co2.registration_tax_eur_cents


def test_co2_below_threshold_no_co2_surcharge() -> None:
    """CO₂ below the threshold must not add any CO₂ surcharge."""
    # co2 = 0 → below 117 g/km threshold → co2 component = 0
    result = compute_import_cost(_eu_params(co2_g_km=0.0, mass_kg=0.0))
    assert result.registration_tax_eur_cents == REG_TAX_BASE_EUR_CENTS


def test_co2_above_threshold_correct_amount() -> None:
    """CO₂ surcharge must equal (co2 - threshold) * rate, rounded to int."""
    co2 = 200.0
    params = _eu_params(co2_g_km=co2, mass_kg=0.0)
    result = compute_import_cost(params)
    excess = co2 - REG_TAX_CO2_THRESHOLD_G_KM
    expected_co2_component = round(excess * REG_TAX_CO2_RATE_EUR_CENTS_PER_G)
    assert result.registration_tax_eur_cents == REG_TAX_BASE_EUR_CENTS + expected_co2_component


def test_mass_component_scales() -> None:
    """Heavier vehicle must produce a larger registration tax."""
    light = compute_import_cost(_eu_params(co2_g_km=0.0, mass_kg=1000.0))
    heavy = compute_import_cost(_eu_params(co2_g_km=0.0, mass_kg=3000.0))
    assert heavy.registration_tax_eur_cents > light.registration_tax_eur_cents


def test_mass_below_threshold_no_mass_surcharge() -> None:
    """Mass below the threshold must not add a mass surcharge."""
    # mass = 500 kg < 2000 kg threshold
    result = compute_import_cost(_eu_params(co2_g_km=0.0, mass_kg=500.0))
    assert result.registration_tax_eur_cents == REG_TAX_BASE_EUR_CENTS


def test_mass_above_threshold_correct_amount() -> None:
    """Mass surcharge must equal (mass - threshold) * rate, rounded to int."""
    mass = 2500.0
    params = _eu_params(co2_g_km=0.0, mass_kg=mass)
    result = compute_import_cost(params)
    excess = mass - REG_TAX_MASS_THRESHOLD_KG
    expected_mass_component = round(excess * REG_TAX_MASS_RATE_EUR_CENTS_PER_KG)
    assert result.registration_tax_eur_cents == REG_TAX_BASE_EUR_CENTS + expected_mass_component


def test_electric_vehicle_zero_co2_component() -> None:
    """Electric vehicles have 0 g/km CO₂, so only the base reg-tax applies (ignoring mass)."""
    result = compute_import_cost(_eu_params(fuel="electric", mass_kg=0.0))
    assert result.registration_tax_eur_cents == REG_TAX_BASE_EUR_CENTS


# ---------------------------------------------------------------------------
# State fee
# ---------------------------------------------------------------------------


def test_state_fee_is_constant() -> None:
    """State fee must equal the declared constant regardless of inputs."""
    eu = compute_import_cost(_eu_params())
    non_eu = compute_import_cost(_non_eu_params())
    assert eu.state_fee_eur_cents == STATE_FEE_EUR_CENTS
    assert non_eu.state_fee_eur_cents == STATE_FEE_EUR_CENTS


# ---------------------------------------------------------------------------
# Total invariant
# ---------------------------------------------------------------------------


def test_total_equals_sum_of_components_eu() -> None:
    """total_landed must equal the sum of all other components for EU origin."""
    result: ImportCostBreakdown = compute_import_cost(_eu_params())
    _assert_total_invariant(result)


def test_total_equals_sum_of_components_non_eu() -> None:
    """total_landed must equal the sum of all other components for non-EU origin."""
    result: ImportCostBreakdown = compute_import_cost(_non_eu_params())
    _assert_total_invariant(result)


def _assert_total_invariant(result: ImportCostBreakdown) -> None:
    expected = (
        result.purchase_price_eur_cents
        + result.transport_eur_cents
        + result.customs_duty_eur_cents
        + result.vat_eur_cents
        + result.registration_tax_eur_cents
        + result.state_fee_eur_cents
    )
    assert result.total_landed_eur_cents == expected


def test_total_invariant_various_scenarios() -> None:
    """Total invariant holds across a matrix of scenarios."""
    scenarios = [
        _eu_params(is_vat_deductible=True),
        _eu_params(first_reg_year=2024),
        _non_eu_params(is_vat_deductible=True),
        _non_eu_params(co2_g_km=250.0, mass_kg=3000.0),
        _eu_params(transport_eur_cents=None),   # estimated transport
        _non_eu_params(transport_eur_cents=None),
    ]
    for params in scenarios:
        result = compute_import_cost(params)
        _assert_total_invariant(result)


# ---------------------------------------------------------------------------
# Transport estimation
# ---------------------------------------------------------------------------


def test_transport_estimated_when_not_provided() -> None:
    """When transport_eur_cents is None, a positive estimate is used."""
    result = compute_import_cost(_eu_params(transport_eur_cents=None))
    assert result.transport_eur_cents > 0


def test_transport_provided_is_used_as_is() -> None:
    """When transport_eur_cents is provided, that exact value is used."""
    result = compute_import_cost(_eu_params(transport_eur_cents=99_999))
    assert result.transport_eur_cents == 99_999


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture
def import_calc_app() -> FastAPI:
    """Minimal FastAPI app with only the import-calculator router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def import_client(import_calc_app: FastAPI) -> AsyncClient:
    """Async HTTP client for the import-calculator app."""
    transport = ASGITransport(app=import_calc_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_get_endpoint_200_eu(import_client: AsyncClient) -> None:
    """GET with all required params for EU origin returns 200."""
    resp = await import_client.get(
        "/v1/import-calculator",
        params={
            "purchase_price_eur_cents": 10_000_00,
            "from_country": "DE",
            "fuel": "petrol",
            "first_reg_year": 2020,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["customs_duty_eur_cents"] == 0
    assert body["total_landed_eur_cents"] > 0


@pytest.mark.anyio
async def test_get_endpoint_200_non_eu(import_client: AsyncClient) -> None:
    """GET with all required params for non-EU origin returns 200 with duty > 0."""
    resp = await import_client.get(
        "/v1/import-calculator",
        params={
            "purchase_price_eur_cents": 8_000_00,
            "from_country": "JP",
            "fuel": "petrol",
            "first_reg_year": 2018,
            "transport_eur_cents": 200_000,
            "co2_g_km": 130.0,
            "mass_kg": 1500.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["customs_duty_eur_cents"] > 0


@pytest.mark.anyio
async def test_get_endpoint_total_invariant_via_http(import_client: AsyncClient) -> None:
    """Total via HTTP must equal the sum of components."""
    resp = await import_client.get(
        "/v1/import-calculator",
        params={
            "purchase_price_eur_cents": 12_000_00,
            "from_country": "JP",
            "fuel": "diesel",
            "first_reg_year": 2018,
            "transport_eur_cents": 200_000,
            "co2_g_km": 160.0,
            "mass_kg": 1800.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    expected = (
        body["purchase_price_eur_cents"]
        + body["transport_eur_cents"]
        + body["customs_duty_eur_cents"]
        + body["vat_eur_cents"]
        + body["registration_tax_eur_cents"]
        + body["state_fee_eur_cents"]
    )
    assert body["total_landed_eur_cents"] == expected


@pytest.mark.anyio
async def test_get_endpoint_400_missing_all_required(import_client: AsyncClient) -> None:
    """GET with no params returns 400 (not 422)."""
    resp = await import_client.get("/v1/import-calculator")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_endpoint_400_missing_some_required(import_client: AsyncClient) -> None:
    """GET with some but not all required params returns 400."""
    resp = await import_client.get(
        "/v1/import-calculator",
        params={
            "purchase_price_eur_cents": 10_000_00,
            "from_country": "DE",
            # fuel and first_reg_year missing
        },
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_post_endpoint_200(import_client: AsyncClient) -> None:
    """POST with valid JSON body returns 200."""
    resp = await import_client.post(
        "/v1/import-calculator",
        json={
            "purchase_price_eur_cents": 15_000_00,
            "from_country": "DE",
            "fuel": "electric",
            "first_reg_year": 2022,
            "transport_eur_cents": 40_000,
            "co2_g_km": None,
            "mass_kg": 2100.0,
            "is_vat_deductible": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # Electric → CO₂ component = 0
    # mass 2100 > 2000 threshold → mass component present
    assert body["customs_duty_eur_cents"] == 0  # EU origin
    assert body["total_landed_eur_cents"] > 0


@pytest.mark.anyio
async def test_post_endpoint_400_missing_required_field(import_client: AsyncClient) -> None:
    """POST missing a required body field returns 422 (Pydantic validation)."""
    resp = await import_client.post(
        "/v1/import-calculator",
        json={
            "purchase_price_eur_cents": 10_000_00,
            # from_country missing
            "fuel": "petrol",
            "first_reg_year": 2020,
        },
    )
    # Pydantic validates required body fields → 422 Unprocessable Entity
    assert resp.status_code == 422
