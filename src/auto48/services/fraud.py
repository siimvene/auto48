"""Fraud-signal service: compute a buyer-facing risk assessment per listing.

Implements the Trust pillar signals from docs/product-scope.md:
  - duplicate_listing    (stolen-vehicle check / duplicate-listing detection)
  - underpriced_vs_market (scam-bait pricing)
  - suspicious_text       (scam-pattern text scoring)
  - incomplete_data       (data-quality signal, low severity)

Design decisions:
  - No new ORM model; everything is computed live.
  - Pure helpers at module level keep text-pattern and scoring logic testable.
  - Weights are named constants; aggregate score is capped at 100.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.adapters.valuation.comparables import ComparablesValuationAdapter
from auto48.models.listing import Listing, ListingStatus
from auto48.models.vehicle import Vehicle

# ---------------------------------------------------------------------------
# Score weights (severity → points added per flag)
# ---------------------------------------------------------------------------

_WEIGHT_HIGH: Final[int] = 50
_WEIGHT_MEDIUM: Final[int] = 25
_WEIGHT_LOW: Final[int] = 10

# Threshold for pct_vs_market to trigger "underpriced_vs_market" signal.
_UNDERPRICED_THRESHOLD: Final[float] = -0.30

# Minimum comparables required to trust the underpriced signal.
_MIN_SAMPLE_SIZE: Final[int] = 3

# Mileage band (±km) for fuzzy duplicate detection when VIN is absent.
_MILEAGE_BAND_KM: Final[int] = 2_000


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


@dataclass
class RiskFlag:
    """A single fraud/risk signal detected on a listing."""

    code: str
    severity: str  # "low" | "medium" | "high"
    detail: str


@dataclass
class RiskAssessment:
    """Aggregate risk result for a listing."""

    score: int  # 0–100
    level: str  # "low" | "medium" | "high"
    flags: list[RiskFlag] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Text-pattern helpers (module-level for unit-testability)
# ---------------------------------------------------------------------------

# Patterns that indicate scam descriptions (case-insensitive).
_SCAM_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"\bshipping\b", re.IGNORECASE),
    re.compile(r"\bforwarding\b", re.IGNORECASE),
    re.compile(r"\bwestern\s+union\b", re.IGNORECASE),
    re.compile(r"\bwire\s+transfer\b", re.IGNORECASE),
    # pay/deposit/payment before viewing/inspection/meeting
    re.compile(
        r"\b(?:pay|deposit|payment)\b.{0,40}\b(?:before|prior\s+to)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"\bagent\b.{0,40}\b(?:on\s+behalf|owner)\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bcontact\b.{0,40}\bemail\s+only\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\boff[-\s]?site\b", re.IGNORECASE),
    re.compile(r"\bno\s+viewing\b", re.IGNORECASE),
]

# Patterns that indicate a placeholder/stub title.
_PLACEHOLDER_TITLE_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"^(test|untitled|new listing|sample|placeholder|lorem)$", re.IGNORECASE),
    re.compile(r"^[xX]{3,}$"),  # "XXX" or similar
]


def _matches_scam_patterns(text: str) -> bool:
    """Return True if *text* matches any known scam pattern."""
    return any(p.search(text) for p in _SCAM_PATTERNS)


def _is_placeholder_title(title: str) -> bool:
    """Return True if *title* looks like a placeholder/stub string."""
    return any(p.match(title.strip()) for p in _PLACEHOLDER_TITLE_PATTERNS)


# ---------------------------------------------------------------------------
# Score aggregation helper
# ---------------------------------------------------------------------------


def _aggregate(flags: list[RiskFlag]) -> tuple[int, str]:
    """Compute (score, level) from a list of flags.

    Each flag contributes its severity weight; total is capped at 100.
    Level is determined from the final score:
      - 0–29  → low
      - 30–59 → medium
      - 60+   → high
    """
    total = 0
    for flag in flags:
        if flag.severity == "high":
            total += _WEIGHT_HIGH
        elif flag.severity == "medium":
            total += _WEIGHT_MEDIUM
        else:
            total += _WEIGHT_LOW
    score = min(total, 100)
    if score >= 60:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"
    return score, level


# ---------------------------------------------------------------------------
# Individual signal checks
# ---------------------------------------------------------------------------


async def _check_duplicate(
    db: AsyncSession,
    listing: Listing,
    vehicle: Vehicle,
) -> RiskFlag | None:
    """Detect duplicate ACTIVE listings.

    Strategy:
    1. If VIN is present: any other ACTIVE listing referencing a Vehicle with
       the same VIN → high severity duplicate.
    2. Otherwise: any other ACTIVE listing (different id) by any seller with
       the same make+model+year and mileage within ±_MILEAGE_BAND_KM of
       the subject's mileage → medium severity duplicate.
    """
    if vehicle.vin:
        stmt = (
            select(Listing.id)
            .join(Vehicle, Listing.vehicle_id == Vehicle.id)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Vehicle.vin == vehicle.vin,
                Listing.id != listing.id,
            )
            .limit(1)
        )
        existing_id = await db.scalar(stmt)
        if existing_id is not None:
            return RiskFlag(
                code="duplicate_listing",
                severity="high",
                detail=(
                    f"Another active listing (id={existing_id}) shares "
                    f"VIN {vehicle.vin}."
                ),
            )
        return None

    # No VIN: fuzzy match on make+model+year+mileage.
    if listing.mileage_km is None:
        return None

    mileage_low = listing.mileage_km - _MILEAGE_BAND_KM
    mileage_high = listing.mileage_km + _MILEAGE_BAND_KM

    stmt2 = (
        select(Listing.id)
        .join(Vehicle, Listing.vehicle_id == Vehicle.id)
        .where(
            Listing.status == ListingStatus.ACTIVE,
            Vehicle.make == vehicle.make,
            Vehicle.model == vehicle.model,
            Vehicle.year == vehicle.year,
            Listing.mileage_km.is_not(None),
            Listing.mileage_km >= mileage_low,
            Listing.mileage_km <= mileage_high,
            Listing.id != listing.id,
        )
        .limit(1)
    )
    existing_id2 = await db.scalar(stmt2)
    if existing_id2 is not None:
        return RiskFlag(
            code="duplicate_listing",
            severity="medium",
            detail=(
                f"Another active listing (id={existing_id2}) matches "
                f"{vehicle.make} {vehicle.model} {vehicle.year} "
                f"with similar mileage."
            ),
        )
    return None


async def _check_underpriced(
    db: AsyncSession,
    listing: Listing,
    vehicle: Vehicle,
) -> RiskFlag | None:
    """Flag listings priced 30%+ below market median (classic scam bait)."""
    adapter = ComparablesValuationAdapter()
    valuation = await adapter.estimate(
        db,
        make=vehicle.make,
        model=vehicle.model,
        year=vehicle.year,
        mileage_km=listing.mileage_km,
        price_eur_cents=listing.price_eur_cents,
    )
    if (
        valuation.pct_vs_market is not None
        and valuation.sample_size >= _MIN_SAMPLE_SIZE
        and valuation.pct_vs_market <= _UNDERPRICED_THRESHOLD
    ):
        pct_display = f"{valuation.pct_vs_market * 100:.1f}%"
        return RiskFlag(
            code="underpriced_vs_market",
            severity="high",
            detail=(
                f"Asking price is {pct_display} below market median "
                f"({valuation.estimate_eur_cents} EUR cents) based on "
                f"{valuation.sample_size} comparables."
            ),
        )
    return None


def _check_scam_text_str(description: str | None) -> RiskFlag | None:
    """Flag listings whose description contains known scam-bait patterns.

    Accepts a plain string (or None) so this helper can be tested without
    constructing an ORM instance.
    """
    if description and _matches_scam_patterns(description):
        return RiskFlag(
            code="suspicious_text",
            severity="high",
            detail=(
                "Description contains language commonly associated with "
                "shipping scams, upfront payment demands, or off-platform "
                "contact requests."
            ),
        )
    return None


def _check_scam_text(listing: Listing) -> RiskFlag | None:
    """Flag listings whose description contains known scam-bait patterns."""
    return _check_scam_text_str(listing.description)


def _check_incomplete_fields(
    title: str,
    description: str | None,
    vin: str | None,
) -> RiskFlag | None:
    """Flag listings with insufficient data.

    Accepts plain Python types so this helper can be tested without ORM objects.

    Args:
        title:       Listing title string.
        description: Listing description, or None.
        vin:         Vehicle VIN, or None.
    """
    placeholder = _is_placeholder_title(title)
    missing_core = (vin is None) and (description is None or description.strip() == "")
    if placeholder or missing_core:
        reasons: list[str] = []
        if missing_core:
            reasons.append("no VIN and no description")
        if placeholder:
            reasons.append("placeholder-looking title")
        return RiskFlag(
            code="incomplete_data",
            severity="low",
            detail="Listing has incomplete data: " + "; ".join(reasons) + ".",
        )
    return None


def _check_incomplete(listing: Listing, vehicle: Vehicle) -> RiskFlag | None:
    """Flag listings with insufficient data (VIN absent AND description absent,
    or a placeholder title).
    """
    return _check_incomplete_fields(listing.title, listing.description, vehicle.vin)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def assess_listing_risk(
    db: AsyncSession,
    listing: Listing,
) -> RiskAssessment:
    """Compute a buyer-facing risk assessment for *listing*.

    Loads the vehicle eagerly if not already loaded, then runs all four
    fraud-signal checks in sequence (duplicate, underpriced, scam text,
    incomplete data) and aggregates to a 0-100 score.

    Args:
        db:      Active async session.
        listing: The listing to assess; ``listing.vehicle`` will be loaded
                 from the DB if not already populated.

    Returns:
        :class:`RiskAssessment` with score, level, and flags list.
    """
    # Ensure vehicle is loaded (may already be eager-loaded by the caller).
    vehicle: Vehicle
    if listing.vehicle_id is not None:
        loaded = await db.get(Vehicle, listing.vehicle_id)
        # Should never be None given FK constraint, but be defensive.
        vehicle = Vehicle.__new__(Vehicle) if loaded is None else loaded
    else:
        vehicle = Vehicle.__new__(Vehicle)

    flags: list[RiskFlag] = []

    dup = await _check_duplicate(db, listing, vehicle)
    if dup is not None:
        flags.append(dup)

    under = await _check_underpriced(db, listing, vehicle)
    if under is not None:
        flags.append(under)

    scam = _check_scam_text(listing)
    if scam is not None:
        flags.append(scam)

    incomplete = _check_incomplete(listing, vehicle)
    if incomplete is not None:
        flags.append(incomplete)

    score, level = _aggregate(flags)
    return RiskAssessment(score=score, level=level, flags=flags)
