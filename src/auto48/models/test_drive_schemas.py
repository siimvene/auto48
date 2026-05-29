"""Pydantic request/response schemas for the test-drive scheduling feature."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from auto48.models.test_drive import TestDriveStatus


class TestDriveCreate(BaseModel):
    slot_at: datetime
    note: str | None = None


class TestDriveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    requester_id: int
    slot_at: datetime
    status: TestDriveStatus
    note: str | None = None
    created_at: datetime
