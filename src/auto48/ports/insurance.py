"""InsurancePort: clean-room protocol for insurance and financing estimates.

Implementations live under adapters/insurance/. All estimates are
approximations — no external API calls in the stub (clean-room invariant).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class InsuranceQuote:
    """Annual and monthly insurance cost estimate.

    ``kind`` is a free-form tag that adapters can use to indicate whether the
    value is a real quote, a market estimate, etc.  The stub always sets it to
    ``"estimate"``.
    """

    annual_eur_cents: int
    monthly_eur_cents: int
    kind: str = "estimate"


@dataclass
class FinancingQuote:
    """Result of a financing (loan/lease) cost computation.

    All monetary fields are in EUR cents.  ``apr_pct`` is the annual
    percentage rate expressed as a plain percentage (e.g. ``6.9`` means 6.9 %).
    """

    monthly_eur_cents: int
    term_months: int
    apr_pct: float
    total_payable_eur_cents: int
    total_interest_eur_cents: int


class InsurancePort(Protocol):
    """Async contract for insurance and financing estimate implementations."""

    async def quote_insurance(
        self,
        *,
        make: str,
        model: str,
        year: int,
        fuel: str,
        power_kw: float | None,
    ) -> InsuranceQuote:
        """Return an annual/monthly insurance cost estimate.

        Args:
            make:     Vehicle manufacturer.
            model:    Vehicle model name.
            year:     Model year (used to derive vehicle age).
            fuel:     Fuel type string (FuelType.value).
            power_kw: Engine power in kW; ``None`` uses a default assumption.

        Returns:
            :class:`InsuranceQuote` with annual and monthly breakdowns.
        """
        ...

    async def quote_financing(
        self,
        *,
        price_eur_cents: int,
        down_payment_eur_cents: int,
        term_months: int,
    ) -> FinancingQuote:
        """Compute monthly payment, total payable, and total interest via annuity.

        Args:
            price_eur_cents:        Vehicle purchase price in EUR cents.
            down_payment_eur_cents: Down payment in EUR cents (may equal price).
            term_months:            Loan term in months (e.g. 60).

        Returns:
            :class:`FinancingQuote` with per-month and totals.
        """
        ...
