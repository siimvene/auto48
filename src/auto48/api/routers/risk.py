"""Risk assessment router: GET /v1/listings/{listing_id}/risk.

Public endpoint (no auth required) — buyers check this before contacting a seller.
Thin handler: delegates all logic to the fraud service.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from auto48.api.dependencies import DbSession
from auto48.models.listing import Listing
from auto48.models.risk_schemas import RiskAssessmentSchema, RiskFlagSchema
from auto48.services.fraud import RiskAssessment, assess_listing_risk

router = APIRouter(prefix="/v1/listings", tags=["risk"])


def _to_schema(assessment: RiskAssessment) -> RiskAssessmentSchema:
    return RiskAssessmentSchema(
        score=assessment.score,
        level=assessment.level,
        flags=[
            RiskFlagSchema(code=f.code, severity=f.severity, detail=f.detail)
            for f in assessment.flags
        ],
    )


@router.get("/{listing_id}/risk", response_model=RiskAssessmentSchema)
async def get_listing_risk(listing_id: int, db: DbSession) -> RiskAssessmentSchema:
    """Return a fraud/risk assessment for the given listing.

    HTTP 404 if the listing does not exist.
    The assessment is computed live (not cached) from:
      - duplicate VIN or same make+model+year+mileage checks
      - market-price undercut detection
      - scam-text pattern matching
      - data-completeness check
    """
    listing = await db.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.vehicle))
    )
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )

    assessment = await assess_listing_risk(db, listing)
    return _to_schema(assessment)
