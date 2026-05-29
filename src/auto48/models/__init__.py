"""Importing this package registers every ORM aggregate on Base.metadata.

Both `create_all` and Alembic autogenerate rely on this single import to see the
full schema; any aggregate omitted here is silently dropped from migrations.
"""

from auto48.models.conversation import Conversation, Message
from auto48.models.history import (
    HistoryEventType,
    VehicleHistoryEvent,
    detect_rollback,
)
from auto48.models.listing import Listing, ListingStatus
from auto48.models.photo import Photo
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User
from auto48.models.vehicle import (
    BodyType,
    Drivetrain,
    FuelType,
    Transmission,
    Vehicle,
)

__all__ = [
    "BodyType",
    "Conversation",
    "Drivetrain",
    "FuelType",
    "HistoryEventType",
    "Listing",
    "ListingStatus",
    "Message",
    "Photo",
    "SellerProfile",
    "SellerType",
    "Transmission",
    "User",
    "Vehicle",
    "VehicleHistoryEvent",
    "detect_rollback",
]
