"""Pydantic response schemas for the valuation endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field

from auto48.ports.valuation import DealScore


class ValuationResponse(BaseModel):
    """Response schema for GET /v1/valuations."""

    estimate_eur_cents: int | None = Field(
        default=None,
        description="Market median price in EUR cents; None when no comparables exist.",
    )
    sample_size: int = Field(
        description="Number of comparable active listings used.",
    )
    deal_score: DealScore = Field(
        description=(
            "How subject price compares to market: "
            "great (<= -15%), good (-15..-5%), fair (-5..+10%), "
            "high (> +10%), unknown (no price / too few comps)."
        ),
    )
    pct_vs_market: float | None = Field(
        default=None,
        description=(
            "Fractional deviation of subject price from median, e.g. -0.12 "
            "means 12 % below market. None when price omitted or no comps."
        ),
    )
    low_eur_cents: int | None = Field(
        default=None,
        description="25th-percentile price (or min) of comparables in EUR cents.",
    )
    high_eur_cents: int | None = Field(
        default=None,
        description="75th-percentile price (or max) of comparables in EUR cents.",
    )
