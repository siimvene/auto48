"""Pydantic response schemas for the risk assessment endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RiskFlagSchema(BaseModel):
    """A single fraud/risk signal with a severity label."""

    code: str = Field(description="Machine-readable flag identifier.")
    severity: str = Field(description="One of: low, medium, high.")
    detail: str = Field(description="Human-readable explanation of the flag.")


class RiskAssessmentSchema(BaseModel):
    """Buyer-facing risk assessment for a listing."""

    score: int = Field(
        ge=0,
        le=100,
        description="Aggregate risk score 0–100; higher means riskier.",
    )
    level: str = Field(description="One of: low, medium, high.")
    flags: list[RiskFlagSchema] = Field(
        default_factory=list,
        description="Individual fraud/risk signals detected.",
    )
