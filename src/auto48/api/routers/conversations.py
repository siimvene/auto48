"""Conversations resource: thin handlers for buyer<->seller messaging.

Follows the thin-handler, RORO, and RFC 7807 error conventions from listings.py.
"""

from fastapi import APIRouter, HTTPException, status

from auto48.api.dependencies import CurrentUser, DbSession
from auto48.models.messaging_schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from auto48.services.messaging import (
    list_conversations_for_user,
    list_messages,
    post_message,
    start_conversation,
)

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ConversationResponse:
    """Start or return an existing conversation for the current buyer."""
    try:
        conversation = await start_conversation(
            db,
            listing_id=payload.listing_id,
            buyer_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=list[ConversationResponse])
async def get_conversations_for_user(
    db: DbSession,
    current_user: CurrentUser,
) -> list[ConversationResponse]:
    """Return all conversations where the current user is buyer or seller."""
    conversations = await list_conversations_for_user(db, user_id=current_user.id)
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: int,
    db: DbSession,
) -> list[MessageResponse]:
    """Return all messages for a conversation ordered by created_at, id."""
    from auto48.models.conversation import Conversation

    exists = await db.get(Conversation, conversation_id)
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    messages = await list_messages(db, conversation_id=conversation_id)
    return [MessageResponse.model_validate(m) for m in messages]


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    conversation_id: int,
    payload: MessageCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    """Post a new message to a conversation as the current user."""
    # Guard empty body (Pydantic min_length gives 422; explicit check gives 400).
    if not payload.body.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message body must not be blank",
        )
    try:
        message = await post_message(
            db,
            conversation_id=conversation_id,
            sender_id=current_user.id,
            body=payload.body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return MessageResponse.model_validate(message)
