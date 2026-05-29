"""Pydantic request/response schemas for the import-cost calculator endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImportCostRequest(BaseModel):
    """Input schema for the import-cost calculator.

    All monetary values are in EUR cents.  Figures are Estonian-market
    approximations — not legal or tax advice.
    """

    purchase_price_eur_cents: int = Field(
        ge=1,
        description="Vehicle purchase price in EUR cents.",
    )
    from_country: str = Field(
        description=(
            "ISO-3166-1 alpha-2 country code (e.g. 'DE', 'JP').  "
            "Used only to determine EU vs. non-EU origin for VAT/customs."
        ),
    )
    transport_eur_cents: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Transport / shipping cost in EUR cents.  "
            "If omitted, an estimate is derived from the origin country."
        ),
    )
    co2_g_km: float | None = Field(
        default=None,
        ge=0,
        description="CO₂ emissions in g/km.  Affects the registration-tax CO₂ component.",
    )
    mass_kg: float | None = Field(
        default=None,
        ge=0,
        description="Vehicle kerb mass in kg.  Affects the registration-tax mass component.",
    )
    fuel: str = Field(
        description=(
            "Fuel type string, e.g. 'petrol', 'diesel', 'electric', "
            "'plugin_hybrid', 'hybrid', 'lpg', 'cng', 'other'."
        ),
    )
    first_reg_year: int = Field(
        ge=1900,
        le=2100,
        description="Year of first registration.  New vehicles (< 2 years old) attract VAT.",
    )
    is_vat_deductible: bool = Field(
        default=False,
        description=(
            "Set True for VAT-registered buyers who can reclaim input VAT.  "
            "When True the VAT component is set to zero (simplification)."
        ),
    )


class ImportCostBreakdown(BaseModel):
    """Per-component import-cost breakdown (all monetary values in EUR cents).

    All figures are Estonian-market approximations — not legal or tax advice.
    """

    purchase_price_eur_cents: int = Field(
        description="Vehicle purchase price as supplied."
    )
    transport_eur_cents: int = Field(
        description="Transport / shipping cost (provided or estimated)."
    )
    customs_duty_eur_cents: int = Field(
        description="Customs duty (~10 % of price + transport) for non-EU imports; 0 for EU."
    )
    vat_eur_cents: int = Field(
        description=(
            "Estonian VAT (22 %) on (price + transport + duty) when applicable; "
            "0 for VAT-deductible buyers."
        )
    )
    registration_tax_eur_cents: int = Field(
        description=(
            "Estonian 2025 motor-vehicle registration tax: "
            "base + CO₂ component + mass component."
        )
    )
    state_fee_eur_cents: int = Field(
        description="Flat state registration / re-registration fee."
    )
    total_landed_eur_cents: int = Field(
        description=(
            "Grand total: purchase_price + transport + customs_duty + vat "
            "+ registration_tax + state_fee."
        )
    )
