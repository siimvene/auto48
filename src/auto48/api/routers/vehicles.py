"""Vehicle data resource: lookup by plate/VIN and history timeline.

Thin async handlers; all heavy lifting delegated to the VehicleDataPort adapter.
Inject the adapter via FastAPI Depends so it can be overridden in tests.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auto48.adapters.vehicle_data import get_vehicle_data_adapter
from auto48.config import get_settings
from auto48.models.history import detect_rollback
from auto48.models.vehicle_data_schemas import (
    VehicleDataResponse,
    VehicleHistoryRecordResponse,
    VehicleHistoryResponse,
)
from auto48.ports.vehicle_data import VehicleDataPort

router = APIRouter(prefix="/v1/vehicles", tags=["vehicles"])


def _get_adapter() -> VehicleDataPort:
    return get_vehicle_data_adapter(get_settings())


VehicleAdapter = Annotated[VehicleDataPort, Depends(_get_adapter)]


@router.get("/lookup", response_model=VehicleDataResponse)
async def lookup_vehicle(
    adapter: VehicleAdapter,
    plate: str | None = Query(default=None),
    vin: str | None = Query(default=None),
) -> VehicleDataResponse:
    """Decode vehicle specification from a plate or VIN.

    Returns 400 if neither plate nor vin is supplied.
    Returns 404 if the vehicle is not found in the data source.
    """
    if not plate and not vin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": "At least one of 'plate' or 'vin' must be provided.",
            },
        )

    result = await adapter.lookup(plate=plate, vin=vin)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "about:blank",
                "title": "Not Found",
                "status": 404,
                "detail": f"No vehicle found for plate={plate!r} vin={vin!r}.",
            },
        )

    return VehicleDataResponse(
        make=result.make,
        model=result.model,
        year=result.year,
        fuel=result.fuel,
        body=result.body,
        transmission=result.transmission,
        variant=result.variant,
        drivetrain=result.drivetrain,
        engine_cc=result.engine_cc,
        power_kw=result.power_kw,
        color=result.color,
        first_registered=result.first_registered,
    )


@router.get("/{vin}/history", response_model=VehicleHistoryResponse)
async def get_vehicle_history(
    vin: str,
    adapter: VehicleAdapter,
) -> VehicleHistoryResponse:
    """Return the provenance timeline for a VIN with a rollback-suspected flag."""
    records = await adapter.history(vin)
    rollback = detect_rollback(records)
    return VehicleHistoryResponse(
        records=[
            VehicleHistoryRecordResponse(
                event_type=r.event_type,
                occurred_at=r.occurred_at,
                source=r.source,
                odometer_km=r.odometer_km,
                detail=r.detail,
            )
            for r in records
        ],
        rollback_suspected=rollback,
    )
