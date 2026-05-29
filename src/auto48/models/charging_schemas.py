"""Pydantic response schema for the EV charging-cost endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChargingCostResponse(BaseModel):
    """Estimated annual and monthly home-charging cost for an EV."""

    battery_kwh: float = Field(description="Battery capacity used for the estimate (kWh).")
    range_km: int = Field(description="Rated range used for the estimate (km).")
    annual_km: int = Field(description="Assumed annual kilometres driven.")
    price_per_kwh_eur_cents: int = Field(
        description="Home electricity price used for the estimate (EUR cents/kWh)."
    )
    consumption_kwh_per_100km: float = Field(
        description="Derived consumption from battery/range (kWh per 100 km)."
    )
    annual_cost_eur_cents: int = Field(
        description="Estimated annual home-charging cost in EUR cents."
    )
    monthly_cost_eur_cents: int = Field(
        description="Estimated monthly home-charging cost in EUR cents (annual / 12, rounded)."
    )
