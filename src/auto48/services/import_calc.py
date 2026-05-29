"""Import-cost calculator service.

Computes the estimated landed cost of importing a vehicle to Estonia.

Components (all EUR-cents, Estonian-market approximations — not legal/tax advice):
  1. Transport         — provided or estimated from origin country.
  2. Customs duty      — ~10 % of (price + transport), non-EU only.
  3. VAT               — Estonian 22 % on (price + transport + duty) when applicable.
  4. Registration tax  — 2025 Estonian motor-vehicle registration tax
                         (base + CO₂ + mass components).
  5. State fee         — flat re-registration / state fee.

All rates and thresholds are encoded as named module constants with inline
comments so reviewers can verify or update them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# EU member-state codes (ISO-3166-1 alpha-2, upper-case).
# Imports from these countries are subject to Estonian VAT rules but NOT to
# the ~10 % non-EU customs duty.
# ---------------------------------------------------------------------------

_EU_COUNTRY_CODES: frozenset[str] = frozenset(
    {
        "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
        "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
        "NL", "PL", "PT", "RO", "SE", "SI", "SK",
    }
)

# ---------------------------------------------------------------------------
# Customs duty
# Applies only to non-EU-origin imports.
# Approximation: EU MFN rate for passenger cars (~6.5 %) + processing margin.
# We use a single blended rate of 10 % for simplicity.
# ---------------------------------------------------------------------------

# Customs duty rate for non-EU imports (fraction of dutiable value).
CUSTOMS_DUTY_RATE: Final[float] = 0.10  # ~10 % — approximate MFN blended rate

# Dutiable base = purchase price + transport (CIF basis, simplified).

# ---------------------------------------------------------------------------
# Value Added Tax
# ---------------------------------------------------------------------------

# Estonian VAT rate (Käibemaksuseadus § 15(1), effective 2024-01-01).
VAT_RATE: Final[float] = 0.22  # 22 %

# A vehicle is considered "new" for VAT purposes if its first registration year
# is within this many years of the reference year.  New vehicles always attract
# VAT regardless of origin.  (Simplification — actual Estonian / EU rules are
# more nuanced; this approximation is documented as an estimate.)
_NEW_VEHICLE_AGE_THRESHOLD: Final[int] = 2  # years
_REFERENCE_YEAR: Final[int] = 2025

# VAT applies when ANY of the following is true:
#   a) The vehicle is "new" (first_reg_year >= REFERENCE_YEAR - threshold), or
#   b) The origin is non-EU (duty already applies — VAT is always assessed).
# VAT does NOT apply when is_vat_deductible is True (buyer reclaims input VAT).
# Simplification note: domestic (EE) second-hand purchases between private
# parties are VAT-exempt; this calculator targets import scenarios and always
# applies VAT when the conditions above are met.

# ---------------------------------------------------------------------------
# Transport cost estimates by origin country / region (EUR cents).
# Used when the caller does not provide transport_eur_cents.
# Values are rough market approximations for 2024–2025.
# ---------------------------------------------------------------------------

_TRANSPORT_ESTIMATE_EUR_CENTS: dict[str, int] = {
    # Nearby EU: short overland haul
    "FI": 15_000,   # ≈ 150 EUR  (Helsinki → Tallinn ferry + delivery)
    "LV": 12_000,   # ≈ 120 EUR
    "LT": 15_000,   # ≈ 150 EUR
    "DE": 40_000,   # ≈ 400 EUR
    "SE": 25_000,   # ≈ 250 EUR  (ferry + delivery)
    # Continental EU
    "FR": 60_000,   # ≈ 600 EUR
    "NL": 50_000,   # ≈ 500 EUR
    "BE": 55_000,   # ≈ 550 EUR
    "IT": 70_000,   # ≈ 700 EUR
    "ES": 75_000,   # ≈ 750 EUR
    "AT": 55_000,   # ≈ 550 EUR
    "PL": 25_000,   # ≈ 250 EUR
    "CZ": 35_000,   # ≈ 350 EUR
    # Non-EU / intercontinental
    "GB": 45_000,   # ≈ 450 EUR  (post-Brexit)
    "JP": 200_000,  # ≈ 2 000 EUR (sea freight)
    "US": 180_000,  # ≈ 1 800 EUR (sea freight)
    "KR": 190_000,  # ≈ 1 900 EUR
    "CN": 180_000,  # ≈ 1 800 EUR
}

# Default transport estimate when the country is not in the lookup.
_TRANSPORT_DEFAULT_EUR_CENTS: Final[int] = 80_000  # ≈ 800 EUR

# ---------------------------------------------------------------------------
# Estonian 2025 motor-vehicle registration tax
# (Mootorsõidukimaks — maanteeamet 2025 rates, simplified approximation)
# ---------------------------------------------------------------------------

# Flat base fee for every vehicle.
REG_TAX_BASE_EUR_CENTS: Final[int] = 50_000  # ≈ 500 EUR — approximate base

# CO₂ component: charged per g/km above the threshold.
REG_TAX_CO2_THRESHOLD_G_KM: Final[float] = 117.0  # g/km — WLTP zero-band threshold
REG_TAX_CO2_RATE_EUR_CENTS_PER_G: Final[float] = 500.0  # ≈ 5 EUR per g/km above threshold

# Mass component: charged per kg above the threshold.
REG_TAX_MASS_THRESHOLD_KG: Final[float] = 2000.0  # kg
REG_TAX_MASS_RATE_EUR_CENTS_PER_KG: Final[float] = 50.0  # ≈ 0.50 EUR per kg above threshold

# Default CO₂ assumed when co2_g_km is not provided.
# Uses a conservative mid-range passenger-car estimate.
_DEFAULT_CO2_G_KM: Final[float] = 150.0  # g/km

# Default mass assumed when mass_kg is not provided.
_DEFAULT_MASS_KG: Final[float] = 1600.0  # kg

# Zero-emission vehicles (electric) have CO₂ = 0, so no CO₂ component.
_ZERO_CO2_FUELS: frozenset[str] = frozenset({"electric"})

# ---------------------------------------------------------------------------
# Flat state re-registration fee (riiklik lõiv)
# Approximate ARK/Transpordiamet fee for changing registration (2024 rates).
# ---------------------------------------------------------------------------

STATE_FEE_EUR_CENTS: Final[int] = 13_000  # ≈ 130 EUR — approximate

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ImportCostParams:
    """Input parameters for :func:`compute_import_cost`.

    Monetary values in EUR cents.  See field comments for semantics.
    """

    purchase_price_eur_cents: int
    from_country: str  # ISO-3166-1 alpha-2, compared upper-case
    fuel: str
    first_reg_year: int
    transport_eur_cents: int | None = None  # None → estimated from country
    co2_g_km: float | None = None           # None → _DEFAULT_CO2_G_KM used
    mass_kg: float | None = None            # None → _DEFAULT_MASS_KG used
    is_vat_deductible: bool = False


@dataclass
class ImportCostBreakdown:
    """Per-component import-cost result.

    All values in EUR cents.  The ``total_landed_eur_cents`` equals the sum of
    all other components + the purchase price — callers can verify this invariant.
    """

    purchase_price_eur_cents: int
    transport_eur_cents: int
    customs_duty_eur_cents: int
    vat_eur_cents: int
    registration_tax_eur_cents: int
    state_fee_eur_cents: int
    total_landed_eur_cents: int


# ---------------------------------------------------------------------------
# Service function
# ---------------------------------------------------------------------------


def compute_import_cost(params: ImportCostParams) -> ImportCostBreakdown:
    """Compute the estimated landed cost of importing a vehicle to Estonia.

    All figures are approximations for illustrative purposes only.
    Not legal or tax advice.

    Args:
        params: :class:`ImportCostParams` describing the vehicle and import.

    Returns:
        :class:`ImportCostBreakdown` with each cost component and the total.
    """
    country_code = params.from_country.upper().strip()
    is_eu = country_code in _EU_COUNTRY_CODES

    # -- Transport -----------------------------------------------------------
    transport: int = (
        params.transport_eur_cents
        if params.transport_eur_cents is not None
        else _TRANSPORT_ESTIMATE_EUR_CENTS.get(country_code, _TRANSPORT_DEFAULT_EUR_CENTS)
    )

    # -- Customs duty --------------------------------------------------------
    # Applies only to non-EU imports on the CIF-simplified dutiable value.
    if is_eu:
        customs_duty: int = 0
    else:
        dutiable_value = params.purchase_price_eur_cents + transport
        customs_duty = int(round(dutiable_value * CUSTOMS_DUTY_RATE))

    # -- VAT -----------------------------------------------------------------
    # Applies when:
    #   (a) vehicle is "new" (registered within _NEW_VEHICLE_AGE_THRESHOLD years), OR
    #   (b) origin is non-EU.
    # Does NOT apply when is_vat_deductible=True (buyer reclaims input VAT).
    # Simplification: VAT base = price + transport + duty (tax-on-tax basis).
    vehicle_age = _REFERENCE_YEAR - params.first_reg_year
    is_new_vehicle = vehicle_age < _NEW_VEHICLE_AGE_THRESHOLD
    vat_applicable = (is_new_vehicle or not is_eu) and not params.is_vat_deductible
    if vat_applicable:
        vat_base = params.purchase_price_eur_cents + transport + customs_duty
        vat: int = int(round(vat_base * VAT_RATE))
    else:
        vat = 0

    # -- Registration tax (2025 Estonian mootorsõidukimaks) ------------------
    # Base component (flat per vehicle).
    reg_tax = REG_TAX_BASE_EUR_CENTS

    # CO₂ component: per g/km above the WLTP threshold.
    if params.fuel in _ZERO_CO2_FUELS:
        effective_co2: float = 0.0
    else:
        effective_co2 = params.co2_g_km if params.co2_g_km is not None else _DEFAULT_CO2_G_KM

    co2_excess = max(0.0, effective_co2 - REG_TAX_CO2_THRESHOLD_G_KM)
    reg_tax += int(round(co2_excess * REG_TAX_CO2_RATE_EUR_CENTS_PER_G))

    # Mass component: per kg above the threshold.
    effective_mass: float = params.mass_kg if params.mass_kg is not None else _DEFAULT_MASS_KG
    mass_excess = max(0.0, effective_mass - REG_TAX_MASS_THRESHOLD_KG)
    reg_tax += int(round(mass_excess * REG_TAX_MASS_RATE_EUR_CENTS_PER_KG))

    # -- State fee -----------------------------------------------------------
    state_fee = STATE_FEE_EUR_CENTS

    # -- Total landed cost ---------------------------------------------------
    total_landed = (
        params.purchase_price_eur_cents
        + transport
        + customs_duty
        + vat
        + reg_tax
        + state_fee
    )

    return ImportCostBreakdown(
        purchase_price_eur_cents=params.purchase_price_eur_cents,
        transport_eur_cents=transport,
        customs_duty_eur_cents=customs_duty,
        vat_eur_cents=vat,
        registration_tax_eur_cents=reg_tax,
        state_fee_eur_cents=state_fee,
        total_landed_eur_cents=total_landed,
    )
