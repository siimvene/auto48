"""Pydantic request/response schemas for the photos resource."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    url: str
    position: int
    processed: bool
    created_at: datetime
