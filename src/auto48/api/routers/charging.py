"""EV charging-cost router.

GET /v1/vehicles/charging-cost
    ?battery_kwh=&range_km=&annual_km=15000&price_per_kwh_eur_cents=1400
    → ChargingCostResponse

Returns HTTP 400 when battery_kwh or range_km is not provided.
Pure computation — no database access.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auto48.models.charging_schemas import ChargingCostResponse
from auto48.services.charging import (
    DEFAULT_ANNUAL_KM,
    DEFAULT_PRICE_PER_KWH_EUR_CENTS,
    charging_cost_eur_cents,
    consumption_kwh_per_100km,
)

router = APIRouter(prefix="/v1/vehicles", tags=["charging"])


@router.get("/charging-cost", response_model=ChargingCostResponse)
async def get_charging_cost(
    battery_kwh: Annotated[
        float | None,
        Query(description="Usable battery capacity in kWh (required)."),
    ] = None,
    range_km: Annotated[
        int | None,
        Query(description="Manufacturer-rated range in kilometres (required)."),
    ] = None,
    annual_km: Annotated[
        int,
        Query(ge=0, le=500_000, description="Estimated annual kilometres driven."),
    ] = DEFAULT_ANNUAL_KM,
    price_per_kwh_eur_cents: Annotated[
        int,
        Query(ge=0, description="Home electricity price in EUR cents per kWh."),
    ] = DEFAULT_PRICE_PER_KWH_EUR_CENTS,
) -> ChargingCostResponse:
    """Estimate annual and monthly home-charging cost for an EV.

    *battery_kwh* and *range_km* are required; omitting either returns HTTP 400.

    The estimate assumes home-only charging and does not account for charging
    losses or public charging sessions.
    """
    if battery_kwh is None or range_km is None:
        missing = []
        if battery_kwh is None:
            missing.append("battery_kwh")
        if range_km is None:
            missing.append("range_km")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Required query parameter(s) missing: {', '.join(missing)}",
        )

    if range_km <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="range_km must be a positive integer.",
        )

    if battery_kwh <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="battery_kwh must be a positive number.",
        )

    consumption = consumption_kwh_per_100km(battery_kwh, range_km)
    # consumption is None only when range_km <= 0, already guarded above.
    assert consumption is not None  # noqa: S101 — invariant guaranteed by guard above

    annual_cost = charging_cost_eur_cents(
        range_km=range_km,
        battery_kwh=battery_kwh,
        annual_km=annual_km,
        price_per_kwh_eur_cents=price_per_kwh_eur_cents,
    )
    monthly_cost = int(round(annual_cost / 12))

    return ChargingCostResponse(
        battery_kwh=battery_kwh,
        range_km=range_km,
        annual_km=annual_km,
        price_per_kwh_eur_cents=price_per_kwh_eur_cents,
        consumption_kwh_per_100km=consumption,
        annual_cost_eur_cents=annual_cost,
        monthly_cost_eur_cents=monthly_cost,
    )
