"""ValuationPort: clean-room protocol for price intelligence.

Implementations live under adapters/valuation/. The port computes
deal scores from our OWN listings only — no external data sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class DealScore(StrEnum):
    """Ordinal label describing how subject price compares to market median."""

    GREAT = "great"
    GOOD = "good"
    FAIR = "fair"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass
class Valuation:
    """Result returned by a valuation estimate.

    ``estimate_eur_cents``, ``low_eur_cents``, and ``high_eur_cents`` are
    ``None`` when there are no comparable listings (sample_size == 0).
    ``pct_vs_market`` is ``None`` when no price was supplied or no comparables
    exist; e.g. -0.12 means the subject is 12 % below the market median.
    """

    estimate_eur_cents: int | None
    sample_size: int
    deal_score: DealScore
    pct_vs_market: float | None
    low_eur_cents: int | None
    high_eur_cents: int | None


class ValuationPort(Protocol):
    """Async contract for price-intelligence implementations."""

    async def estimate(
        self,
        db: AsyncSession,
        *,
        make: str,
        model: str,
        year: int,
        mileage_km: int | None,
        price_eur_cents: int | None,
    ) -> Valuation:
        """Return a market valuation for the described vehicle.

        Args:
            db:               Active async SQLAlchemy session.
            make:             Vehicle manufacturer (e.g. "Toyota").
            model:            Vehicle model (e.g. "Corolla").
            year:             Model year (e.g. 2019).
            mileage_km:       Odometer reading in km; may be None.
            price_eur_cents:  Subject asking price in EUR cents; may be None.

        Returns:
            A :class:`Valuation` populated from comparable active listings.
        """
        ...
