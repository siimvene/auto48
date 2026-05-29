"""Import-cost calculator router.

POST /v1/import-calculator
    Accepts a JSON body → ImportCostBreakdown

GET  /v1/import-calculator
    Accepts all fields as query parameters → ImportCostBreakdown

Both endpoints are equivalent; the POST variant is preferred for rich inputs.
No authentication required — this is a pure stateless calculation.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auto48.models.import_calc_schemas import (
    ImportCostBreakdown,
    ImportCostRequest,
)
from auto48.services.import_calc import (
    ImportCostBreakdown as ServiceBreakdown,
)
from auto48.services.import_calc import (
    ImportCostParams,
    compute_import_cost,
)

router = APIRouter(prefix="/v1/import-calculator", tags=["import-calculator"])


def _to_response(bd: ServiceBreakdown) -> ImportCostBreakdown:
    """Map the service dataclass to the Pydantic response schema."""
    return ImportCostBreakdown(
        purchase_price_eur_cents=bd.purchase_price_eur_cents,
        transport_eur_cents=bd.transport_eur_cents,
        customs_duty_eur_cents=bd.customs_duty_eur_cents,
        vat_eur_cents=bd.vat_eur_cents,
        registration_tax_eur_cents=bd.registration_tax_eur_cents,
        state_fee_eur_cents=bd.state_fee_eur_cents,
        total_landed_eur_cents=bd.total_landed_eur_cents,
    )


@router.post("", response_model=ImportCostBreakdown)
async def post_import_cost(body: ImportCostRequest) -> ImportCostBreakdown:
    """Calculate the estimated landed import cost from a JSON body.

    All figures are Estonian-market approximations — not legal or tax advice.
    """
    params = ImportCostParams(
        purchase_price_eur_cents=body.purchase_price_eur_cents,
        from_country=body.from_country,
        fuel=body.fuel,
        first_reg_year=body.first_reg_year,
        transport_eur_cents=body.transport_eur_cents,
        co2_g_km=body.co2_g_km,
        mass_kg=body.mass_kg,
        is_vat_deductible=body.is_vat_deductible,
    )
    return _to_response(compute_import_cost(params))


@router.get("", response_model=ImportCostBreakdown)
async def get_import_cost(
    purchase_price_eur_cents: Annotated[
        int | None,
        Query(ge=1, description="Vehicle purchase price in EUR cents."),
    ] = None,
    from_country: Annotated[
        str | None,
        Query(description="ISO-3166-1 alpha-2 origin country code, e.g. 'DE'."),
    ] = None,
    fuel: Annotated[
        str | None,
        Query(description="Fuel type: petrol, diesel, electric, hybrid, …"),
    ] = None,
    first_reg_year: Annotated[
        int | None,
        Query(ge=1900, le=2100, description="Year of first vehicle registration."),
    ] = None,
    transport_eur_cents: Annotated[
        int | None,
        Query(ge=0, description="Transport cost in EUR cents (estimated if omitted)."),
    ] = None,
    co2_g_km: Annotated[
        float | None,
        Query(ge=0, description="CO₂ emissions in g/km (default estimate used if omitted)."),
    ] = None,
    mass_kg: Annotated[
        float | None,
        Query(ge=0, description="Kerb mass in kg (default estimate used if omitted)."),
    ] = None,
    is_vat_deductible: Annotated[
        bool,
        Query(description="True for VAT-registered buyers who reclaim input VAT."),
    ] = False,
) -> ImportCostBreakdown:
    """Calculate the estimated landed import cost from query parameters.

    Required: purchase_price_eur_cents, from_country, fuel, first_reg_year.
    All figures are Estonian-market approximations — not legal or tax advice.
    """
    missing: list[str] = []
    if purchase_price_eur_cents is None:
        missing.append("purchase_price_eur_cents")
    if from_country is None:
        missing.append("from_country")
    if fuel is None:
        missing.append("fuel")
    if first_reg_year is None:
        missing.append("first_reg_year")

    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required query parameter(s): {', '.join(missing)}",
        )

    # All four required fields are confirmed non-None by the guard above.
    assert purchase_price_eur_cents is not None
    assert from_country is not None
    assert fuel is not None
    assert first_reg_year is not None

    params = ImportCostParams(
        purchase_price_eur_cents=purchase_price_eur_cents,
        from_country=from_country,
        fuel=fuel,
        first_reg_year=first_reg_year,
        transport_eur_cents=transport_eur_cents,
        co2_g_km=co2_g_km,
        mass_kg=mass_kg,
        is_vat_deductible=is_vat_deductible,
    )
    return _to_response(compute_import_cost(params))
