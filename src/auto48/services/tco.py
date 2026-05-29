"""TCO (Total Cost of Ownership) service.

Computes a multi-year breakdown of ownership costs for a listing.

Components (all EUR-cents, Estonian-market approximations):
  1. Registration / motor tax  — flat annual fee by fuel type.
  2. Fuel or charging cost     — annual_km × assumed per-unit price × consumption.
  3. Maintenance               — rises with vehicle age and annual mileage.
  4. Insurance                 — delegated to InsurancePort.
  5. Depreciation              — simple exponential decay on the asking price.

Named constants below document every assumption so callers can review or
override them in future iterations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.models.listing import Listing
from auto48.models.vehicle import Vehicle
from auto48.ports.insurance import InsurancePort

# ---------------------------------------------------------------------------
# Motor tax / annual registration fee (EUR cents)
# Estonian ARK motor vehicle annual tax approximation, 2024 rates.
# ---------------------------------------------------------------------------

_REGISTRATION_FEE_EUR_CENTS: dict[str, int] = {
    "electric": 0,           # BEVs currently exempt in Estonia
    "plugin_hybrid": 4_500,  # ≈ 45 EUR
    "hybrid": 6_000,         # ≈ 60 EUR
    "petrol": 9_000,         # ≈ 90 EUR
    "diesel": 10_500,        # ≈ 105 EUR (diesel surcharge)
    "lpg": 8_500,            # ≈ 85 EUR
    "cng": 8_500,            # ≈ 85 EUR
    "other": 9_000,          # fallback
}

# ---------------------------------------------------------------------------
# Fuel / charging cost assumptions
# ---------------------------------------------------------------------------

# Assumed consumption by fuel type (per 100 km).
_CONSUMPTION_PER_100KM: dict[str, float] = {
    "petrol": 7.5,        # litres per 100 km
    "diesel": 6.0,        # litres per 100 km
    "hybrid": 5.5,        # litres per 100 km (self-charging)
    "plugin_hybrid": 3.0, # litres per 100 km (blended)
    "electric": 18.0,     # kWh per 100 km
    "lpg": 10.0,          # litres per 100 km (LPG has lower energy density)
    "cng": 8.0,           # kg per 100 km (CNG)
    "other": 7.5,         # fallback
}

# Unit energy price in EUR cents (approximate Estonian pump/grid prices 2024).
_UNIT_PRICE_EUR_CENTS: dict[str, int] = {
    "petrol": 175,        # ≈ 1.75 EUR / litre
    "diesel": 165,        # ≈ 1.65 EUR / litre
    "hybrid": 175,        # same as petrol
    "plugin_hybrid": 90,  # blended: partly grid (≈ 0.15 EUR/kWh) + partly petrol
    "electric": 18,       # ≈ 0.18 EUR / kWh (home charging)
    "lpg": 75,            # ≈ 0.75 EUR / litre
    "cng": 120,           # ≈ 1.20 EUR / kg
    "other": 175,         # fallback
}

# ---------------------------------------------------------------------------
# Maintenance cost assumptions
# ---------------------------------------------------------------------------

# Base annual maintenance cost in EUR cents (≈ 500 EUR for a modern car).
_MAINTENANCE_BASE_EUR_CENTS: Final[int] = 50_000

# Maintenance age factor: cost rises 5 % per year of vehicle age at start.
_MAINTENANCE_AGE_RATE: Final[float] = 0.05

# Maintenance mileage surcharge: extra 0.1 EUR per km over 15 000 km/year.
_MAINTENANCE_MILEAGE_EXTRA_PER_KM_CENTS: Final[float] = 10.0  # 0.10 EUR / km

# Reference annual km (no surcharge below this).
_MAINTENANCE_BASE_ANNUAL_KM: Final[int] = 15_000

# Electric vehicles have lower maintenance costs (no oil changes, fewer brakes).
_MAINTENANCE_EV_DISCOUNT: Final[float] = 0.30

# ---------------------------------------------------------------------------
# Depreciation assumptions
# ---------------------------------------------------------------------------

# Annual depreciation rate: the vehicle loses this fraction of remaining value
# each year.  Based on a typical Estonian used-car market curve.
_DEPRECIATION_RATE: Final[float] = 0.12  # 12 % per year (residual value method)

# ---------------------------------------------------------------------------
# Reference year for age calculations.
# ---------------------------------------------------------------------------
_REFERENCE_YEAR: Final[int] = 2025


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class YearBreakdown:
    """Per-year ownership cost breakdown (all values in EUR cents)."""

    year: int  # 1-based year index (year 1 = first 12 months of ownership)
    registration_eur_cents: int
    fuel_eur_cents: int
    maintenance_eur_cents: int
    insurance_eur_cents: int
    depreciation_eur_cents: int
    total_eur_cents: int


@dataclass
class TcoBreakdown:
    """Multi-year total cost of ownership result.

    ``years`` is an ordered list of :class:`YearBreakdown` objects.
    ``total_*`` fields are the sum across all years.
    """

    listing_id: int
    years_count: int
    annual_km: int
    per_year: list[YearBreakdown] = field(default_factory=list)

    # Totals (sum of per_year components — guaranteed to equal sum(y.total) by
    # construction so tests can assert both sides independently).
    total_registration_eur_cents: int = 0
    total_fuel_eur_cents: int = 0
    total_maintenance_eur_cents: int = 0
    total_insurance_eur_cents: int = 0
    total_depreciation_eur_cents: int = 0
    total_eur_cents: int = 0


# ---------------------------------------------------------------------------
# Service function
# ---------------------------------------------------------------------------


async def compute_tco(
    db: AsyncSession,
    listing: Listing,
    *,
    years: int,
    annual_km: int = 15_000,
    adapter: InsurancePort,
) -> TcoBreakdown:
    """Compute a multi-year TCO breakdown for the given listing.

    Fetches the related Vehicle directly (avoids async lazy-load issues).

    Args:
        db:         Active async SQLAlchemy session.
        listing:    Listing ORM object (must have valid vehicle_id).
        years:      Number of ownership years to project (>= 1).
        annual_km:  Estimated km driven per year (default 15 000).
        adapter:    InsurancePort implementation for insurance quotes.

    Returns:
        :class:`TcoBreakdown` with per-year list and aggregated totals.

    Raises:
        ValueError: if years < 1 or annual_km < 0.
        RuntimeError: if the vehicle record cannot be found.
    """
    if years < 1:
        raise ValueError(f"years must be >= 1, got {years}")
    if annual_km < 0:
        raise ValueError(f"annual_km must be >= 0, got {annual_km}")

    # Load vehicle directly to avoid async lazy-load.
    vehicle: Vehicle | None = await db.scalar(
        select(Vehicle).where(Vehicle.id == listing.vehicle_id)
    )
    if vehicle is None:
        raise RuntimeError(f"Vehicle {listing.vehicle_id} not found for listing {listing.id}")

    fuel_str: str = vehicle.fuel.value  # FuelType enum → string key

    # Extract power_kw from specs JSON (may be absent).
    power_kw: float | None = None
    if vehicle.specs is not None:
        raw = vehicle.specs.get("power_kw")
        if raw is not None:
            try:
                power_kw = float(raw)
            except (TypeError, ValueError):
                power_kw = None

    # Vehicle age at start of ownership.
    vehicle_age_at_start: int = max(0, _REFERENCE_YEAR - vehicle.year)

    # ---- Insurance quote (same for every year in the stub; real adapter may vary) ----
    ins_quote = await adapter.quote_insurance(
        make=vehicle.make,
        model=vehicle.model,
        year=vehicle.year,
        fuel=fuel_str,
        power_kw=power_kw,
    )
    annual_insurance = ins_quote.annual_eur_cents

    # ---- Per-unit fuel/energy price and consumption ----
    consumption = _CONSUMPTION_PER_100KM.get(fuel_str, _CONSUMPTION_PER_100KM["other"])
    unit_price = _UNIT_PRICE_EUR_CENTS.get(fuel_str, _UNIT_PRICE_EUR_CENTS["other"])
    # Annual fuel cost = annual_km / 100 × consumption × unit_price
    annual_fuel = int(round((annual_km / 100.0) * consumption * unit_price))

    # ---- Registration fee (constant each year) ----
    annual_registration = _REGISTRATION_FEE_EUR_CENTS.get(
        fuel_str, _REGISTRATION_FEE_EUR_CENTS["other"]
    )

    # ---- Starting value for depreciation (listing asking price) ----
    current_value_cents: float = float(listing.price_eur_cents)

    # ---- Accumulate per-year breakdown ----
    per_year: list[YearBreakdown] = []

    # Running totals (built from per_year so sum invariant holds).
    total_registration = 0
    total_fuel = 0
    total_maintenance = 0
    total_insurance = 0
    total_depreciation = 0

    for yr_idx in range(1, years + 1):
        # Age of vehicle at the start of this ownership year.
        age_this_year = vehicle_age_at_start + (yr_idx - 1)

        # Maintenance: base × (1 + age_rate × age) × mileage_factor × ev_discount
        maintenance_factor = 1.0 + _MAINTENANCE_AGE_RATE * age_this_year
        if annual_km > _MAINTENANCE_BASE_ANNUAL_KM:
            excess_km = annual_km - _MAINTENANCE_BASE_ANNUAL_KM
            mileage_extra = int(round(excess_km * _MAINTENANCE_MILEAGE_EXTRA_PER_KM_CENTS))
        else:
            mileage_extra = 0

        base_maint = int(round(_MAINTENANCE_BASE_EUR_CENTS * maintenance_factor))
        annual_maintenance = base_maint + mileage_extra
        if fuel_str == "electric":
            annual_maintenance = int(round(annual_maintenance * (1.0 - _MAINTENANCE_EV_DISCOUNT)))

        # Depreciation: value lost in this year = current_value × rate.
        depreciation_this_year = int(round(current_value_cents * _DEPRECIATION_RATE))
        current_value_cents = current_value_cents * (1.0 - _DEPRECIATION_RATE)

        year_total = (
            annual_registration
            + annual_fuel
            + annual_maintenance
            + annual_insurance
            + depreciation_this_year
        )

        per_year.append(
            YearBreakdown(
                year=yr_idx,
                registration_eur_cents=annual_registration,
                fuel_eur_cents=annual_fuel,
                maintenance_eur_cents=annual_maintenance,
                insurance_eur_cents=annual_insurance,
                depreciation_eur_cents=depreciation_this_year,
                total_eur_cents=year_total,
            )
        )

        total_registration += annual_registration
        total_fuel += annual_fuel
        total_maintenance += annual_maintenance
        total_insurance += annual_insurance
        total_depreciation += depreciation_this_year

    grand_total = (
        total_registration
        + total_fuel
        + total_maintenance
        + total_insurance
        + total_depreciation
    )

    return TcoBreakdown(
        listing_id=listing.id,
        years_count=years,
        annual_km=annual_km,
        per_year=per_year,
        total_registration_eur_cents=total_registration,
        total_fuel_eur_cents=total_fuel,
        total_maintenance_eur_cents=total_maintenance,
        total_insurance_eur_cents=total_insurance,
        total_depreciation_eur_cents=total_depreciation,
        total_eur_cents=grand_total,
    )
