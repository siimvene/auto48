"""Escrow service layer: place, release, and refund buyer deposits.

All DB I/O is async; callers supply the session and adapter so this layer stays
unit-testable without the FastAPI DI machinery.

Exceptions raised here are mapped to HTTP status codes in the router:
  DepositNotFound        → 404
  DepositPermissionError → 403
  DepositAlreadySettled  → 409
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.models.escrow import Deposit, DepositStatus
from auto48.models.listing import Listing
from auto48.models.seller import SellerProfile
from auto48.ports.payment import PaymentPort

# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class DepositNotFound(Exception):
    """Raised when a deposit (or its related listing) does not exist."""


class DepositPermissionError(Exception):
    """Raised when the actor is not authorised to perform the operation."""


class DepositAlreadySettled(Exception):
    """Raised when attempting to settle a deposit that is not in HELD status."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_listing_seller_user_id(db: AsyncSession, listing_id: int) -> int:
    """Return the user_id of the seller who owns *listing_id*.

    Raises DepositNotFound if the listing or its seller profile does not exist.
    """
    listing = await db.scalar(select(Listing).where(Listing.id == listing_id))
    if listing is None:
        raise DepositNotFound(f"Listing {listing_id} not found.")

    seller = await db.scalar(
        select(SellerProfile).where(SellerProfile.id == listing.seller_id)
    )
    if seller is None:
        raise DepositNotFound(f"Seller profile for listing {listing_id} not found.")

    return seller.user_id


async def _require_held(deposit: Deposit) -> None:
    """Raise DepositAlreadySettled if the deposit is not HELD."""
    if deposit.status is not DepositStatus.HELD:
        raise DepositAlreadySettled(
            f"Deposit {deposit.id} is already settled (status={deposit.status.value})."
        )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def place_deposit(
    db: AsyncSession,
    listing_id: int,
    buyer_id: int,
    amount_eur_cents: int,
    adapter: PaymentPort,
) -> Deposit:
    """Hold a buyer deposit for a listing via the payment provider.

    Args:
        db: Active async session.
        listing_id: The listing the buyer is depositing against.
        buyer_id: The authenticated buyer's user id.
        amount_eur_cents: Amount to hold in EUR cents.
        adapter: Payment adapter used to initiate the hold.

    Returns:
        Persisted Deposit ORM object with status HELD.

    Raises:
        DepositNotFound: If the listing does not exist (caller should 404).
    """
    # Verify listing exists (seller lookup is a side-effect; we just need existence).
    await _get_listing_seller_user_id(db, listing_id)

    deposit = Deposit(
        listing_id=listing_id,
        buyer_id=buyer_id,
        amount_eur_cents=amount_eur_cents,
        status=DepositStatus.HELD,
    )
    db.add(deposit)
    await db.flush()  # populate deposit.id before calling provider

    result = await adapter.hold_deposit(
        amount_eur_cents=amount_eur_cents,
        reference=f"deposit:{deposit.id}",
    )
    deposit.provider_ref = result.provider_id
    if result.status == "failed":
        deposit.status = DepositStatus.FAILED

    await db.flush()
    await db.refresh(deposit)
    return deposit


async def release(
    db: AsyncSession,
    deposit_id: int,
    actor_user_id: int,
    adapter: PaymentPort,
) -> Deposit:
    """Release a held deposit to the seller.

    Only the listing's seller user may call this.

    Args:
        db: Active async session.
        deposit_id: ID of the Deposit to release.
        actor_user_id: User id of the caller (must be the seller).
        adapter: Payment adapter used to release the hold.

    Returns:
        Updated Deposit ORM object with status RELEASED.

    Raises:
        DepositNotFound: If the deposit or its listing does not exist.
        DepositPermissionError: If actor is not the listing's seller.
        DepositAlreadySettled: If deposit is not in HELD status.
    """
    deposit = await db.scalar(select(Deposit).where(Deposit.id == deposit_id))
    if deposit is None:
        raise DepositNotFound(f"Deposit {deposit_id} not found.")

    seller_user_id = await _get_listing_seller_user_id(db, deposit.listing_id)
    if actor_user_id != seller_user_id:
        raise DepositPermissionError("Only the listing's seller may release a deposit.")

    await _require_held(deposit)

    if deposit.provider_ref is None:
        raise DepositAlreadySettled(
            f"Deposit {deposit_id} has no provider reference; cannot release."
        )

    result = await adapter.release_deposit(deposit.provider_ref)
    deposit.status = DepositStatus.RELEASED
    deposit.provider_ref = result.provider_id
    await db.flush()
    await db.refresh(deposit)
    return deposit


async def refund(
    db: AsyncSession,
    deposit_id: int,
    actor_user_id: int,
    adapter: PaymentPort,
) -> Deposit:
    """Refund a held deposit back to the buyer.

    Either the listing's seller or the buyer themselves may refund.

    Args:
        db: Active async session.
        deposit_id: ID of the Deposit to refund.
        actor_user_id: User id of the caller (seller or buyer).
        adapter: Payment adapter used to issue the refund.

    Returns:
        Updated Deposit ORM object with status REFUNDED.

    Raises:
        DepositNotFound: If the deposit or its listing does not exist.
        DepositPermissionError: If actor is neither the seller nor the buyer.
        DepositAlreadySettled: If deposit is not in HELD status.
    """
    deposit = await db.scalar(select(Deposit).where(Deposit.id == deposit_id))
    if deposit is None:
        raise DepositNotFound(f"Deposit {deposit_id} not found.")

    seller_user_id = await _get_listing_seller_user_id(db, deposit.listing_id)
    is_seller = actor_user_id == seller_user_id
    is_buyer = actor_user_id == deposit.buyer_id

    if not is_seller and not is_buyer:
        raise DepositPermissionError(
            "Only the listing's seller or the deposit buyer may refund a deposit."
        )

    await _require_held(deposit)

    if deposit.provider_ref is None:
        raise DepositAlreadySettled(
            f"Deposit {deposit_id} has no provider reference; cannot refund."
        )

    result = await adapter.refund_deposit(deposit.provider_ref)
    deposit.status = DepositStatus.REFUNDED
    deposit.provider_ref = result.provider_id
    await db.flush()
    await db.refresh(deposit)
    return deposit


async def list_deposits(
    db: AsyncSession,
    user_id: int,
) -> list[Deposit]:
    """Return all deposits where the user is the buyer or the listing's seller.

    Args:
        db: Active async session.
        user_id: The authenticated user whose deposits to return.

    Returns:
        List of Deposit ORM objects, newest first.
    """
    rows = await db.scalars(
        select(Deposit)
        .join(Listing, Deposit.listing_id == Listing.id)
        .join(SellerProfile, Listing.seller_id == SellerProfile.id)
        .where(
            or_(
                Deposit.buyer_id == user_id,
                SellerProfile.user_id == user_id,
            )
        )
        .distinct()
        .order_by(Deposit.created_at.desc())
    )
    return list(rows.all())
