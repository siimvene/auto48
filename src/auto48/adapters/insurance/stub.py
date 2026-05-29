"""StubInsuranceAdapter: deterministic offline estimates for dev and tests.

All values are computed from a simple formula — no network calls, safe for CI.

Insurance model (Estonian-market approximation):
  base_annual = BASE_INSURANCE_EUR_CENTS
  scaled by vehicle value band (from inferred value via age curve),
  age factor (newer cars cost more per year), and
  power factor (higher kW → higher premium).

Financing model:
  Standard annuity formula with a fixed DEFAULT_APR_PCT constant.
  M = P * r / (1 - (1+r)^-n)  where r = APR/100/12.
  Special case: r == 0 → M = P / n.
"""

from __future__ import annotations

import math
from typing import Final

from auto48.ports.insurance import FinancingQuote, InsuranceQuote

# ---------------------------------------------------------------------------
# Insurance constants (Estonian-market approximations)
# ---------------------------------------------------------------------------

# Base annual premium for a typical car (EUR cents, ≈ 400 EUR).
_BASE_INSURANCE_EUR_CENTS: Final[int] = 40_000

# Default power assumption when power_kw is unknown (kW).
_DEFAULT_POWER_KW: Final[float] = 100.0

# Power scaling: each kW above the default adds this fraction to base premium.
_POWER_SCALE_PER_KW: Final[float] = 0.003  # 0.3 % per extra kW above default

# Age scaling: annual premium increases 2 % per year of vehicle age.
_AGE_PREMIUM_RATE: Final[float] = 0.02

# Electric/plugin_hybrid discount fraction (lower risk, lower maintenance cost).
_EV_DISCOUNT: Final[float] = 0.15  # 15 % off for electric/plugin_hybrid

# Reference year used for age calculation.
_REFERENCE_YEAR: Final[int] = 2025

# ---------------------------------------------------------------------------
# Financing constants
# ---------------------------------------------------------------------------

# Default annual percentage rate in percent (e.g. 6.9 %).
DEFAULT_APR_PCT: Final[float] = 6.9


class StubInsuranceAdapter:
    """Deterministic insurance/financing estimates — safe for dev and CI."""

    async def quote_insurance(
        self,
        *,
        make: str,
        model: str,
        year: int,
        fuel: str,
        power_kw: float | None,
    ) -> InsuranceQuote:
        """Estimate annual insurance from age, power, and fuel type.

        The formula is deterministic and proportional — same inputs → same output.

        Args:
            make:     Vehicle manufacturer (unused in stub, reserved for future).
            model:    Vehicle model (unused in stub, reserved for future).
            year:     Model year (used to compute vehicle age).
            fuel:     Fuel type string.  Electric/plugin_hybrid get a discount.
            power_kw: Engine power in kW; None uses ``_DEFAULT_POWER_KW``.

        Returns:
            InsuranceQuote with ``kind="estimate"``.
        """
        # pylint: disable=unused-argument
        effective_power = power_kw if power_kw is not None else _DEFAULT_POWER_KW

        age = max(0, _REFERENCE_YEAR - year)

        # Age multiplier: base + 2 % per year of age (capped at 2× base).
        age_multiplier = min(2.0, 1.0 + age * _AGE_PREMIUM_RATE)

        # Power multiplier: scales proportionally above the default.
        excess_kw = max(0.0, effective_power - _DEFAULT_POWER_KW)
        power_multiplier = 1.0 + excess_kw * _POWER_SCALE_PER_KW

        annual = int(round(_BASE_INSURANCE_EUR_CENTS * age_multiplier * power_multiplier))

        # Discount for low-emission fuels.
        if fuel in ("electric", "plugin_hybrid"):
            annual = int(round(annual * (1.0 - _EV_DISCOUNT)))

        monthly = int(round(annual / 12))
        return InsuranceQuote(
            annual_eur_cents=annual,
            monthly_eur_cents=monthly,
            kind="estimate",
        )

    async def quote_financing(
        self,
        *,
        price_eur_cents: int,
        down_payment_eur_cents: int,
        term_months: int,
    ) -> FinancingQuote:
        """Compute monthly payment using the standard annuity formula.

        M = P * r / (1 - (1+r)^-n)
        where P = principal (price - down), r = APR/100/12, n = term_months.

        Edge cases:
        - r == 0 → M = P / n (interest-free).
        - principal <= 0 → all zeros (down payment >= price).
        - n <= 0 → raises ValueError.

        Args:
            price_eur_cents:        Vehicle purchase price in EUR cents.
            down_payment_eur_cents: Down payment in EUR cents.
            term_months:            Loan term in months (must be > 0).

        Returns:
            FinancingQuote with monthly payment, totals and APR.

        Raises:
            ValueError: if term_months <= 0.
        """
        if term_months <= 0:
            raise ValueError(f"term_months must be positive, got {term_months}")

        principal = max(0, price_eur_cents - down_payment_eur_cents)

        if principal == 0:
            return FinancingQuote(
                monthly_eur_cents=0,
                term_months=term_months,
                apr_pct=DEFAULT_APR_PCT,
                total_payable_eur_cents=0,
                total_interest_eur_cents=0,
            )

        r = DEFAULT_APR_PCT / 100.0 / 12.0  # monthly rate

        if r == 0.0:
            monthly = principal / term_months
        else:
            monthly = principal * r / (1.0 - math.pow(1.0 + r, -term_months))

        monthly_cents = int(round(monthly))
        total_payable = monthly_cents * term_months
        total_interest = total_payable - principal

        return FinancingQuote(
            monthly_eur_cents=monthly_cents,
            term_months=term_months,
            apr_pct=DEFAULT_APR_PCT,
            total_payable_eur_cents=total_payable,
            total_interest_eur_cents=total_interest,
        )
