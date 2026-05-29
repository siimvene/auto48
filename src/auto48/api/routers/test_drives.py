"""Test-drive scheduling resource: thin handlers (RORO, RFC 7807, CurrentUser).

Routes:
  POST  /v1/listings/{listing_id}/test-drives  – buyer requests a test drive
  GET   /v1/test-drives                        – current user's bookings
  POST  /v1/test-drives/{id}/confirm           – seller confirms
  POST  /v1/test-drives/{id}/decline           – seller declines
  POST  /v1/test-drives/{id}/cancel            – requester cancels
"""

from fastapi import APIRouter, HTTPException, status

from auto48.api.dependencies import CurrentUser, DbSession
from auto48.models.test_drive import TestDriveStatus
from auto48.models.test_drive_schemas import TestDriveCreate, TestDriveResponse
from auto48.services.test_drive import (
    PermissionError as TestDrivePermissionError,
)
from auto48.services.test_drive import (
    list_for_user,
    request_test_drive,
    set_status,
)

router = APIRouter(tags=["test-drives"])


@router.post(
    "/v1/listings/{listing_id}/test-drives",
    response_model=TestDriveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_drive(
    listing_id: int,
    payload: TestDriveCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> TestDriveResponse:
    """Request a test drive on a listing as the current (buyer) user."""
    try:
        booking = await request_test_drive(
            db,
            listing_id=listing_id,
            requester_id=current_user.id,
            slot_at=payload.slot_at,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return TestDriveResponse.model_validate(booking)


@router.get("/v1/test-drives", response_model=list[TestDriveResponse])
async def get_test_drives_for_user(
    db: DbSession,
    current_user: CurrentUser,
) -> list[TestDriveResponse]:
    """Return all test-drive bookings where the current user is requester or seller."""
    bookings = await list_for_user(db, user_id=current_user.id)
    return [TestDriveResponse.model_validate(b) for b in bookings]


@router.post(
    "/v1/test-drives/{booking_id}/confirm",
    response_model=TestDriveResponse,
)
async def confirm_test_drive(
    booking_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> TestDriveResponse:
    """Confirm a test-drive booking (seller only)."""
    try:
        booking = await set_status(
            db,
            booking_id=booking_id,
            actor_user_id=current_user.id,
            new_status=TestDriveStatus.CONFIRMED,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except TestDrivePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return TestDriveResponse.model_validate(booking)


@router.post(
    "/v1/test-drives/{booking_id}/decline",
    response_model=TestDriveResponse,
)
async def decline_test_drive(
    booking_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> TestDriveResponse:
    """Decline a test-drive booking (seller only)."""
    try:
        booking = await set_status(
            db,
            booking_id=booking_id,
            actor_user_id=current_user.id,
            new_status=TestDriveStatus.DECLINED,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except TestDrivePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return TestDriveResponse.model_validate(booking)


@router.post(
    "/v1/test-drives/{booking_id}/cancel",
    response_model=TestDriveResponse,
)
async def cancel_test_drive(
    booking_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> TestDriveResponse:
    """Cancel a test-drive booking (requester only)."""
    try:
        booking = await set_status(
            db,
            booking_id=booking_id,
            actor_user_id=current_user.id,
            new_status=TestDriveStatus.CANCELLED,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except TestDrivePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return TestDriveResponse.model_validate(booking)
