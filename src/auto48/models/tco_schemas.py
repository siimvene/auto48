"""Pydantic response schemas for TCO and financing endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class YearBreakdownSchema(BaseModel):
    """Per-year ownership cost breakdown (all monetary values in EUR cents)."""

    year: int = Field(description="1-based year index (1 = first 12 months of ownership).")
    registration_eur_cents: int = Field(description="Annual motor tax / registration fee.")
    fuel_eur_cents: int = Field(description="Annual fuel or charging cost.")
    maintenance_eur_cents: int = Field(description="Annual maintenance and servicing cost.")
    insurance_eur_cents: int = Field(description="Annual insurance premium estimate.")
    depreciation_eur_cents: int = Field(description="Value lost in this year.")
    total_eur_cents: int = Field(description="Sum of all components for this year.")


class TcoBreakdownSchema(BaseModel):
    """Multi-year total cost of ownership response."""

    listing_id: int = Field(description="ID of the listing this breakdown applies to.")
    years_count: int = Field(description="Number of projected ownership years.")
    annual_km: int = Field(description="Assumed annual kilometres driven.")
    per_year: list[YearBreakdownSchema] = Field(
        description="Per-year cost breakdown, ordered from year 1 to years_count."
    )
    total_registration_eur_cents: int = Field(
        description="Cumulative registration/motor-tax cost over all years."
    )
    total_fuel_eur_cents: int = Field(
        description="Cumulative fuel or charging cost over all years."
    )
    total_maintenance_eur_cents: int = Field(
        description="Cumulative maintenance cost over all years."
    )
    total_insurance_eur_cents: int = Field(
        description="Cumulative insurance cost over all years."
    )
    total_depreciation_eur_cents: int = Field(
        description="Cumulative depreciation (value lost) over all years."
    )
    total_eur_cents: int = Field(
        description="Grand total: sum of all components across all years."
    )


class FinancingQuoteSchema(BaseModel):
    """Response schema for the financing quote endpoint."""

    monthly_eur_cents: int = Field(description="Monthly payment in EUR cents.")
    term_months: int = Field(description="Loan term in months.")
    apr_pct: float = Field(description="Annual percentage rate (e.g. 6.9 means 6.9 %).")
    total_payable_eur_cents: int = Field(
        description="Total amount payable over the loan term (monthly × term)."
    )
    total_interest_eur_cents: int = Field(
        description="Total interest paid (total_payable − principal)."
    )
