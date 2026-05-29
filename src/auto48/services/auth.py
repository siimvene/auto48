"""Authentication service layer: register, authenticate, lookup.

All DB I/O is async; callers supply the session so this layer stays
unit-testable without the FastAPI DI machinery.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.core.security import hash_password, verify_password
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Return the User with *email* or None if not found."""
    user: User | None = await db.scalar(select(User).where(User.email == email))
    return user


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    seller_type: SellerType,
) -> User:
    """Create a new User + SellerProfile and flush to the session.

    The caller is responsible for committing the transaction (the request-scoped
    ``get_db`` dependency commits on success automatically).

    Raises:
        ValueError: if *email* is already taken.
    """
    existing = await get_user_by_email(db, email)
    if existing is not None:
        raise ValueError(f"Email already registered: {email}")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    await db.flush()  # populate user.id

    profile = SellerProfile(user_id=user.id, type=seller_type)
    db.add(profile)
    await db.flush()
    await db.refresh(user)  # materialise server_default fields (created_at)
    return user


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User | None:
    """Return the User if credentials are valid; None otherwise.

    A None return should become HTTP 401 — callers decide on the response shape.
    """
    user = await get_user_by_email(db, email)
    if user is None:
        return None
    if not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
