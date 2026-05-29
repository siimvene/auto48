"""Saved-searches resource: create / list / delete.

POST   /v1/saved-searches         — create (auth required)
GET    /v1/saved-searches         — list current user's searches (auth required)
DELETE /v1/saved-searches/{id}    — delete own search (auth required; 403 non-owner)

All errors follow RFC 7807.
"""

from fastapi import APIRouter, HTTPException, status

from auto48.api.dependencies import CurrentUser, DbSession
from auto48.models.saved_search_schemas import SavedSearchCreate, SavedSearchResponse
from auto48.services.saved_search import (
    create_saved_search,
    delete_saved_search,
    get_saved_search,
    list_saved_searches,
)

router = APIRouter(prefix="/v1/saved-searches", tags=["saved-searches"])


@router.post("", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
async def create(
    payload: SavedSearchCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> SavedSearchResponse:
    """Create a new saved search for the authenticated user."""
    saved_search = await create_saved_search(
        db,
        user_id=current_user.id,
        name=payload.name,
        query=payload.query.model_dump(exclude_none=True),
    )
    return SavedSearchResponse.model_validate(saved_search)


@router.get("", response_model=list[SavedSearchResponse])
async def list_mine(
    db: DbSession,
    current_user: CurrentUser,
) -> list[SavedSearchResponse]:
    """Return all saved searches owned by the authenticated user."""
    searches = await list_saved_searches(db, user_id=current_user.id)
    return [SavedSearchResponse.model_validate(s) for s in searches]


@router.delete("/{saved_search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    saved_search_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete a saved search.  Returns 404 if not found, 403 if not the owner."""
    saved_search = await get_saved_search(db, saved_search_id=saved_search_id)
    if saved_search is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search {saved_search_id} not found",
        )
    if saved_search.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this saved search",
        )
    await delete_saved_search(db, saved_search=saved_search)
