"""Stolen-vehicle check resource: deterministic flag lookup by VIN.

Thin async handler; all logic delegated to the StolenVehiclePort adapter.
Inject the adapter via FastAPI Depends so it can be overridden in tests.
Public endpoint — no authentication required (buyers need to check before purchase).
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from auto48.adapters.stolen import get_stolen_adapter
from auto48.config import get_settings
from auto48.models.stolen_schemas import StolenCheckResponse
from auto48.ports.stolen import StolenVehiclePort

router = APIRouter(prefix="/v1/vehicles", tags=["stolen"])

# Basic VIN validation: 8–17 uppercase alphanumeric characters.
# Intentionally permissive — real ISO 3779 parsing is left to future real adapters.
_VIN_RE = re.compile(r"^[A-Z0-9]{8,17}$")


def _get_adapter() -> StolenVehiclePort:
    return get_stolen_adapter(get_settings())


StolenAdapter = Annotated[StolenVehiclePort, Depends(_get_adapter)]


@router.get("/{vin}/stolen-check", response_model=StolenCheckResponse)
async def stolen_check(
    vin: str,
    adapter: StolenAdapter,
) -> StolenCheckResponse:
    """Check whether a VIN appears in the stolen-vehicle registry.

    Returns 400 if the VIN is obviously invalid (wrong length or charset).
    Returns 200 with flagged=True if the vehicle is listed as stolen.
    Returns 200 with flagged=False if the vehicle is not flagged.
    """
    normalised = vin.upper().strip()
    if not _VIN_RE.match(normalised):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": (
                    f"Invalid VIN {vin!r}: must be 8–17 uppercase alphanumeric characters."
                ),
            },
        )

    result = await adapter.check(normalised)
    return StolenCheckResponse(
        vin=result.vin,
        flagged=result.flagged,
        source=result.source,
        detail=result.detail,
    )
