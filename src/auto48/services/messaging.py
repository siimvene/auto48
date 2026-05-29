"""Buyer<->seller messaging service functions.

All functions accept an AsyncSession and return ORM objects. Callers are
responsible for committing the session.
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.models.conversation import Conversation, Message
from auto48.models.listing import Listing
from auto48.models.seller import SellerProfile


async def start_conversation(
    db: AsyncSession,
    listing_id: int,
    buyer_id: int,
) -> Conversation:
    """Return an existing conversation for (listing, buyer) or create a new one.

    Resolves the seller by following: Listing.seller_id → SellerProfile.user_id.
    The returned conversation's seller_id is the *user* id, not the profile id.
    """
    # Resolve listing and seller chain.
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise ValueError(f"Listing {listing_id} not found")

    profile = await db.get(SellerProfile, listing.seller_id)
    if profile is None:
        raise ValueError(f"SellerProfile {listing.seller_id} not found")

    seller_user_id = profile.user_id

    # Reuse an existing conversation if one already exists for this (listing, buyer) pair.
    existing = await db.scalar(
        select(Conversation).where(
            Conversation.listing_id == listing_id,
            Conversation.buyer_id == buyer_id,
        )
    )
    if existing is not None:
        return existing

    conversation = Conversation(
        listing_id=listing_id,
        buyer_id=buyer_id,
        seller_id=seller_user_id,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


async def post_message(
    db: AsyncSession,
    conversation_id: int,
    sender_id: int,
    body: str,
) -> Message:
    """Append a message to an existing conversation."""
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    message = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        body=body,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def list_messages(
    db: AsyncSession,
    conversation_id: int,
) -> list[Message]:
    """Return all messages for a conversation ordered by created_at, then id."""
    rows = await db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
    )
    return list(rows.all())


async def list_conversations_for_user(
    db: AsyncSession,
    user_id: int,
) -> list[Conversation]:
    """Return all conversations where the user is the buyer or seller."""
    rows = await db.scalars(
        select(Conversation).where(
            or_(
                Conversation.buyer_id == user_id,
                Conversation.seller_id == user_id,
            )
        )
    )
    return list(rows.all())
