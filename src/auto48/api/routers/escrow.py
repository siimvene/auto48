"""Escrow router: buyer deposit, release, and refund endpoints.

POST /v1/listings/{listing_id}/deposit  — buyer places a deposit → 201 Deposit
POST /v1/deposits/{id}/release          — seller releases deposit to themselves
POST /v1/deposits/{id}/refund           — seller or buyer refunds deposit to buyer
GET  /v1/deposits                       — current user's deposits (buyer or seller)

RFC 7807 errors; thin handlers, all logic delegated to services.escrow.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from auto48.adapters.payment import get_payment_adapter
from auto48.api.dependencies import CurrentUser, DbSession
from auto48.config import get_settings
from auto48.models.escrow_schemas import DepositResponse, PlaceDepositRequest
from auto48.ports.payment import PaymentPort
from auto48.services.escrow import (
    DepositAlreadySettled,
    DepositNotFound,
    DepositPermissionError,
    list_deposits,
    place_deposit,
    refund,
    release,
)

router = APIRouter(prefix="/v1", tags=["escrow"])


def _get_payment_adapter() -> PaymentPort:
    return get_payment_adapter(get_settings())


PaymentAdapter = Annotated[PaymentPort, Depends(_get_payment_adapter)]


@router.post(
    "/listings/{listing_id}/deposit",
    response_model=DepositResponse,
    status_code=status.HTTP_201_CREATED,
)
async def place_listing_deposit(
    listing_id: int,
    payload: PlaceDepositRequest,
    current_user: CurrentUser,
    db: DbSession,
    adapter: PaymentAdapter,
) -> DepositResponse:
    """Place a refundable deposit on a listing.

    Raises 404 if the listing does not exist.
    """
    try:
        deposit = await place_deposit(
            db,
            listing_id=listing_id,
            buyer_id=current_user.id,
            amount_eur_cents=payload.amount_eur_cents,
            adapter=adapter,
        )
    except DepositNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return DepositResponse.model_validate(deposit)


@router.post(
    "/deposits/{deposit_id}/release",
    response_model=DepositResponse,
)
async def release_deposit(
    deposit_id: int,
    current_user: CurrentUser,
    db: DbSession,
    adapter: PaymentAdapter,
) -> DepositResponse:
    """Release a held deposit to the seller.

    Raises 404 if the deposit is not found.
    Raises 403 if the caller is not the listing's seller.
    Raises 409 if the deposit is already settled.
    """
    try:
        deposit = await release(db, deposit_id, current_user.id, adapter)
    except DepositNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DepositPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except DepositAlreadySettled as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return DepositResponse.model_validate(deposit)


@router.post(
    "/deposits/{deposit_id}/refund",
    response_model=DepositResponse,
)
async def refund_deposit(
    deposit_id: int,
    current_user: CurrentUser,
    db: DbSession,
    adapter: PaymentAdapter,
) -> DepositResponse:
    """Refund a held deposit to the buyer.

    Raises 404 if the deposit is not found.
    Raises 403 if the caller is neither the seller nor the buyer.
    Raises 409 if the deposit is already settled.
    """
    try:
        deposit = await refund(db, deposit_id, current_user.id, adapter)
    except DepositNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DepositPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except DepositAlreadySettled as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return DepositResponse.model_validate(deposit)


@router.get(
    "/deposits",
    response_model=list[DepositResponse],
)
async def get_deposits(
    current_user: CurrentUser,
    db: DbSession,
) -> list[DepositResponse]:
    """Return all deposits where the current user is the buyer or the listing's seller."""
    deposits = await list_deposits(db, current_user.id)
    return [DepositResponse.model_validate(d) for d in deposits]
