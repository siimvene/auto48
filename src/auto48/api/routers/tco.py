"""TCO router: price intelligence endpoints.

GET /v1/listings/{listing_id}/tco?years=5&annual_km=15000
    → TcoBreakdownSchema

GET /v1/listings/{listing_id}/financing?down_payment_eur_cents=0&term_months=60
    → FinancingQuoteSchema
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from auto48.adapters.insurance import get_insurance_adapter
from auto48.api.dependencies import DbSession
from auto48.config import get_settings
from auto48.models.listing import Listing
from auto48.models.tco_schemas import (
    FinancingQuoteSchema,
    TcoBreakdownSchema,
    YearBreakdownSchema,
)
from auto48.services.tco import compute_tco

router = APIRouter(prefix="/v1/listings", tags=["tco"])

# Module-level adapter singleton (stub for now; factory makes it swappable).
_insurance_adapter = get_insurance_adapter(get_settings())


@router.get("/{listing_id}/tco", response_model=TcoBreakdownSchema)
async def get_tco(
    listing_id: int,
    db: DbSession,
    years: Annotated[
        int,
        Query(ge=1, le=20, description="Number of ownership years to project (1–20)."),
    ] = 5,
    annual_km: Annotated[
        int,
        Query(ge=0, le=200_000, description="Estimated annual kilometres driven."),
    ] = 15_000,
) -> TcoBreakdownSchema:
    """Return a multi-year total cost of ownership breakdown for a listing.

    Raises HTTP 404 if the listing is not found.
    """
    listing = await db.scalar(select(Listing).where(Listing.id == listing_id))
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )

    breakdown = await compute_tco(
        db,
        listing,
        years=years,
        annual_km=annual_km,
        adapter=_insurance_adapter,
    )

    return TcoBreakdownSchema(
        listing_id=breakdown.listing_id,
        years_count=breakdown.years_count,
        annual_km=breakdown.annual_km,
        per_year=[
            YearBreakdownSchema(
                year=y.year,
                registration_eur_cents=y.registration_eur_cents,
                fuel_eur_cents=y.fuel_eur_cents,
                maintenance_eur_cents=y.maintenance_eur_cents,
                insurance_eur_cents=y.insurance_eur_cents,
                depreciation_eur_cents=y.depreciation_eur_cents,
                total_eur_cents=y.total_eur_cents,
            )
            for y in breakdown.per_year
        ],
        total_registration_eur_cents=breakdown.total_registration_eur_cents,
        total_fuel_eur_cents=breakdown.total_fuel_eur_cents,
        total_maintenance_eur_cents=breakdown.total_maintenance_eur_cents,
        total_insurance_eur_cents=breakdown.total_insurance_eur_cents,
        total_depreciation_eur_cents=breakdown.total_depreciation_eur_cents,
        total_eur_cents=breakdown.total_eur_cents,
    )


@router.get("/{listing_id}/financing", response_model=FinancingQuoteSchema)
async def get_financing(
    listing_id: int,
    db: DbSession,
    down_payment_eur_cents: Annotated[
        int,
        Query(ge=0, description="Down payment in EUR cents (0 = no down payment)."),
    ] = 0,
    term_months: Annotated[
        int,
        Query(ge=1, le=360, description="Loan term in months (1–360)."),
    ] = 60,
) -> FinancingQuoteSchema:
    """Return a financing quote for the given listing.

    Raises HTTP 404 if the listing is not found.
    """
    listing = await db.scalar(select(Listing).where(Listing.id == listing_id))
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )

    quote = await _insurance_adapter.quote_financing(
        price_eur_cents=listing.price_eur_cents,
        down_payment_eur_cents=down_payment_eur_cents,
        term_months=term_months,
    )

    return FinancingQuoteSchema(
        monthly_eur_cents=quote.monthly_eur_cents,
        term_months=quote.term_months,
        apr_pct=quote.apr_pct,
        total_payable_eur_cents=quote.total_payable_eur_cents,
        total_interest_eur_cents=quote.total_interest_eur_cents,
    )
