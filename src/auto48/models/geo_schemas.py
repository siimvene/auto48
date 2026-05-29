"""Pydantic response schemas for geo/proximity endpoints."""

from pydantic import BaseModel

from auto48.models.schemas import ListingResponse


class NearbyListing(BaseModel):
    """A listing together with its computed distance from the query point."""

    listing: ListingResponse
    distance_km: float
