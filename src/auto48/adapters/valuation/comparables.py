"""ComparablesValuationAdapter: price intelligence from our own active listings.

Queries ONLY the platform's own Listing/Vehicle data — no external calls,
no competitor scraping (clean-room invariant from docs/product-scope.md).

Deal-score thresholds (subject vs. median):
  <= -15 %  → great
  > -15 % and <= -5 %  → good
  > -5 %  and <= +10 % → fair
  > +10 %              → high
  no price / < 3 comps → unknown
"""

from __future__ import annotations

import statistics
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.models.listing import Listing, ListingStatus
from auto48.models.vehicle import Vehicle
from auto48.ports.valuation import DealScore, Valuation

# Minimum number of comparable listings required before we trust the estimate.
_MIN_SAMPLE: Final[int] = 3

# Year window: ±2 years from the subject year.
_YEAR_BAND: Final[int] = 2

# Mileage band: ±30 % of the subject odometer.
_MILEAGE_PCT: Final[float] = 0.30


def _deal_score(pct: float) -> DealScore:
    """Map a fractional deviation from median to a deal-score label.

    Args:
        pct: (subject_price - median) / median, e.g. -0.12 is 12 % below.

    Returns:
        DealScore enum value.
    """
    if pct <= -0.15:
        return DealScore.GREAT
    if pct <= -0.05:
        return DealScore.GOOD
    if pct <= 0.10:
        return DealScore.FAIR
    return DealScore.HIGH


class ComparablesValuationAdapter:
    """Implements :class:`~auto48.ports.valuation.ValuationPort` via DB comparables."""

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
        """Compute a market estimate from active comparable listings.

        Strategy:
        1. Fetch all ACTIVE listings for the same make+model within ±2 years.
        2. If ``mileage_km`` is given and the result set is >=``_MIN_SAMPLE``,
           narrow by a ±30 % mileage band.  If the narrowed set drops below
           the threshold, fall back to the wider year-band set so we always
           report what we can.
        3. Compute median (estimate) and p25/p75 (low/high band) using stdlib.
        4. Map subject price deviation to a deal_score if price is given and
           sample is adequate; otherwise return ``DealScore.UNKNOWN``.

        Args:
            db:               Active async SQLAlchemy session.
            make:             Vehicle manufacturer.
            model:            Vehicle model name.
            year:             Model year of the subject vehicle.
            mileage_km:       Odometer reading in km; ``None`` to skip band.
            price_eur_cents:  Subject asking price in EUR cents; ``None`` means
                              the deal score will be ``UNKNOWN``.

        Returns:
            :class:`~auto48.ports.valuation.Valuation` populated from comps.
        """
        # --- 1. Fetch year-band comparables ---
        year_comps = await self._fetch_prices(
            db,
            make=make,
            model=model,
            year_min=year - _YEAR_BAND,
            year_max=year + _YEAR_BAND,
        )

        # --- 2. Optionally narrow by mileage band ---
        prices: list[int]
        if mileage_km is not None and len(year_comps) >= _MIN_SAMPLE:
            band = int(mileage_km * _MILEAGE_PCT)
            mileage_comps = await self._fetch_prices(
                db,
                make=make,
                model=model,
                year_min=year - _YEAR_BAND,
                year_max=year + _YEAR_BAND,
                mileage_min=mileage_km - band,
                mileage_max=mileage_km + band,
            )
            prices = mileage_comps if len(mileage_comps) >= _MIN_SAMPLE else year_comps
        else:
            prices = year_comps

        sample_size = len(prices)

        # --- 3. No comparables at all ---
        if sample_size == 0:
            return Valuation(
                estimate_eur_cents=None,
                sample_size=0,
                deal_score=DealScore.UNKNOWN,
                pct_vs_market=None,
                low_eur_cents=None,
                high_eur_cents=None,
            )

        # --- 4. Compute estimate and band ---
        estimate = int(round(statistics.median(prices)))

        if sample_size >= 4:
            # quantiles(n=4) gives [p25, p50, p75]
            qs = statistics.quantiles(prices, n=4)
            low = int(round(qs[0]))
            high = int(round(qs[2]))
        else:
            low = min(prices)
            high = max(prices)

        # --- 5. Deal score ---
        if price_eur_cents is None or sample_size < _MIN_SAMPLE:
            return Valuation(
                estimate_eur_cents=estimate,
                sample_size=sample_size,
                deal_score=DealScore.UNKNOWN,
                pct_vs_market=None,
                low_eur_cents=low,
                high_eur_cents=high,
            )

        pct = (price_eur_cents - estimate) / estimate
        return Valuation(
            estimate_eur_cents=estimate,
            sample_size=sample_size,
            deal_score=_deal_score(pct),
            pct_vs_market=pct,
            low_eur_cents=low,
            high_eur_cents=high,
        )

    @staticmethod
    async def _fetch_prices(
        db: AsyncSession,
        *,
        make: str,
        model: str,
        year_min: int,
        year_max: int,
        mileage_min: int | None = None,
        mileage_max: int | None = None,
    ) -> list[int]:
        """Return price_eur_cents for all ACTIVE listings matching the criteria.

        Args:
            db:          Async session.
            make:        Exact make (case-sensitive as stored).
            model:       Exact model (case-sensitive as stored).
            year_min:    Minimum model year (inclusive).
            year_max:    Maximum model year (inclusive).
            mileage_min: Optional minimum mileage in km (inclusive).
            mileage_max: Optional maximum mileage in km (inclusive).

        Returns:
            List of prices in EUR cents.
        """
        stmt = (
            select(Listing.price_eur_cents)
            .join(Vehicle, Listing.vehicle_id == Vehicle.id)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Vehicle.make == make,
                Vehicle.model == model,
                Vehicle.year >= year_min,
                Vehicle.year <= year_max,
            )
        )

        if mileage_min is not None:
            stmt = stmt.where(
                Listing.mileage_km.is_not(None),
                Listing.mileage_km >= mileage_min,
            )
        if mileage_max is not None:
            stmt = stmt.where(
                Listing.mileage_km.is_not(None),
                Listing.mileage_km <= mileage_max,
            )

        rows = (await db.scalars(stmt)).all()
        return list(rows)
