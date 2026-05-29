"""Natural-language search router.

GET /v1/search?q=...&limit=&offset=
Returns parsed facets + paginated ACTIVE listings matching them.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auto48.api.dependencies import DbSession
from auto48.models.nl_schemas import NLSearchResponse, ParsedQueryResponse
from auto48.models.schemas import ListingResponse
from auto48.services.nl_search import ParsedQuery, run

router = APIRouter(prefix="/v1/search", tags=["nl-search"])


def _pq_to_response(pq: ParsedQuery) -> ParsedQueryResponse:
    return ParsedQueryResponse(
        make=pq.make,
        model=pq.model,
        fuel=pq.fuel,
        body=pq.body,
        transmission=pq.transmission,
        year_min=pq.year_min,
        year_max=pq.year_max,
        price_max_eur_cents=pq.price_max_eur_cents,
        price_min_eur_cents=pq.price_min_eur_cents,
        mileage_max=pq.mileage_max,
    )


@router.get("", response_model=NLSearchResponse)
async def nl_search(
    db: DbSession,
    q: Annotated[
        str | None,
        Query(description="Natural-language search query (ET/EN)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NLSearchResponse:
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' is required and must not be empty.",
        )

    pq, listings, total = await run(db, q, limit=limit, offset=offset)

    def _to_listing_response(record: object) -> ListingResponse:
        from auto48.models.listing import Listing  # local import to avoid cycles

        assert isinstance(record, Listing)
        resp = ListingResponse.model_validate(record)
        resp.thumbnail_url = record.photos[0].url if record.photos else None
        return resp

    return NLSearchResponse(
        parsed=_pq_to_response(pq),
        items=[_to_listing_response(r) for r in listings],
        total=total,
        limit=limit,
        offset=offset,
    )
