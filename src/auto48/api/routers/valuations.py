"""Valuations router: GET /v1/valuations — deal-score from our own comparables."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auto48.adapters.valuation.comparables import ComparablesValuationAdapter
from auto48.api.dependencies import DbSession
from auto48.models.valuation_schemas import ValuationResponse

router = APIRouter(prefix="/v1/valuations", tags=["valuations"])

_adapter = ComparablesValuationAdapter()


@router.get("", response_model=ValuationResponse)
async def get_valuation(
    db: DbSession,
    make: Annotated[
        str | None,
        Query(description="Vehicle manufacturer (required)."),
    ] = None,
    model: Annotated[
        str | None,
        Query(description="Vehicle model (required)."),
    ] = None,
    year: Annotated[
        int | None,
        Query(ge=1900, le=2100, description="Model year (required)."),
    ] = None,
    mileage_km: Annotated[
        int | None,
        Query(ge=0, description="Odometer reading in km (optional)."),
    ] = None,
    price_eur_cents: Annotated[
        int | None,
        Query(ge=0, description="Subject asking price in EUR cents (optional)."),
    ] = None,
) -> ValuationResponse:
    """Return a market valuation for the described vehicle.

    Requires **make**, **model**, and **year**.  Returns HTTP 400 if any of
    these three are missing.

    ``mileage_km`` and ``price_eur_cents`` are optional:

    - Without ``price_eur_cents`` the ``deal_score`` is always ``unknown``.
    - Without ``mileage_km`` the mileage-narrowing step is skipped.
    """
    missing: list[str] = []
    if make is None:
        missing.append("make")
    if model is None:
        missing.append("model")
    if year is None:
        missing.append("year")
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Required query parameters missing: {', '.join(missing)}",
        )

    # Narrow types: the guard above guarantees these are non-None at this point.
    assert make is not None
    assert model is not None
    assert year is not None

    valuation = await _adapter.estimate(
        db,
        make=make,
        model=model,
        year=year,
        mileage_km=mileage_km,
        price_eur_cents=price_eur_cents,
    )

    return ValuationResponse(
        estimate_eur_cents=valuation.estimate_eur_cents,
        sample_size=valuation.sample_size,
        deal_score=valuation.deal_score,
        pct_vs_market=valuation.pct_vs_market,
        low_eur_cents=valuation.low_eur_cents,
        high_eur_cents=valuation.high_eur_cents,
    )
