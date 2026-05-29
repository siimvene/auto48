"""Pure helpers for EV charging-cost estimation.

All functions are side-effect-free and unit-testable without a database.

Default constants (document sources so they can be updated):
  DEFAULT_ANNUAL_KM        — typical Estonian annual mileage (Statistics Estonia 2023).
  DEFAULT_PRICE_PER_KWH    — average Estonian home electricity tariff, EUR cents/kWh
                             (Elering 2024 household average: ~14 EUR cents/kWh = 1400 cents).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Public constants (used as endpoint defaults)
# ---------------------------------------------------------------------------

#: Typical annual kilometres for a passenger car in Estonia (Statistics Estonia 2023).
DEFAULT_ANNUAL_KM: int = 15_000

#: Average Estonian home electricity price in EUR *cents* per kWh (Elering 2024 avg ≈ 14 c/kWh).
DEFAULT_PRICE_PER_KWH_EUR_CENTS: int = 1_400


# ---------------------------------------------------------------------------
# Pure computation helpers
# ---------------------------------------------------------------------------


def consumption_kwh_per_100km(battery_kwh: float, range_km: int) -> float | None:
    """Estimate average energy consumption from battery capacity and rated range.

    Returns *None* when *range_km* is zero or negative to avoid division by zero.

    Args:
        battery_kwh: Usable battery capacity in kilowatt-hours.
        range_km: Manufacturer-rated range in kilometres (WLTP or similar).

    Returns:
        Consumption in kWh per 100 km, or *None* if the range is invalid.
    """
    if range_km <= 0:
        return None
    return (battery_kwh / range_km) * 100.0


def charging_cost_eur_cents(
    *,
    range_km: int,
    battery_kwh: float,
    annual_km: int = DEFAULT_ANNUAL_KM,
    price_per_kwh_eur_cents: int = DEFAULT_PRICE_PER_KWH_EUR_CENTS,
) -> int:
    """Estimate annual home-charging cost in EUR cents.

    The calculation assumes the driver charges exclusively at home at the
    given tariff.  Real-world costs differ due to charging losses (~10–15 %),
    public charging sessions, and variable tariffs — treat this as a
    lower-bound home-only estimate.

    Formula::

        consumption = battery_kwh / range_km * 100   [kWh/100 km]
        annual_kwh  = consumption / 100 * annual_km
        annual_cost = annual_kwh * price_per_kwh_eur_cents

    Args:
        range_km: Rated range in kilometres (must be > 0).
        battery_kwh: Usable battery capacity in kWh.
        annual_km: Estimated annual distance driven (default: 15 000 km).
        price_per_kwh_eur_cents: Home electricity price in EUR cents per kWh
            (default: 1 400 cents = 14 EUR cents/kWh).

    Returns:
        Estimated annual charging cost in EUR cents (rounded to nearest cent).

    Raises:
        ValueError: If *range_km* is zero or negative.
    """
    if range_km <= 0:
        raise ValueError(f"range_km must be positive, got {range_km}")

    kwh_per_100km = battery_kwh / range_km * 100.0
    annual_kwh = kwh_per_100km / 100.0 * annual_km
    return int(round(annual_kwh * price_per_kwh_eur_cents))
