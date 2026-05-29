"""Importing this package registers every ORM aggregate on Base.metadata.

Both `create_all` and Alembic autogenerate rely on this single import to see the
full schema; any aggregate omitted here is silently dropped from migrations.
"""

from auto48.models.billing import (
    Promotion,
    PromotionKind,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from auto48.models.conversation import Conversation, Message
from auto48.models.dealer_feed import (
    DealerFeed,
    FeedFormat,
    IngestRun,
    IngestStatus,
)
from auto48.models.history import (
    HistoryEventType,
    VehicleHistoryEvent,
    detect_rollback,
)
from auto48.models.listing import Listing, ListingStatus
from auto48.models.photo import Photo
from auto48.models.saved_search import Alert, SavedSearch
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.test_drive import TestDriveBooking, TestDriveStatus
from auto48.models.user import User
from auto48.models.vehicle import (
    BodyType,
    Drivetrain,
    FuelType,
    Transmission,
    Vehicle,
)

__all__ = [
    "Alert",
    "BodyType",
    "Conversation",
    "DealerFeed",
    "Drivetrain",
    "FeedFormat",
    "FuelType",
    "HistoryEventType",
    "IngestRun",
    "IngestStatus",
    "Listing",
    "ListingStatus",
    "Message",
    "Photo",
    "Promotion",
    "PromotionKind",
    "SavedSearch",
    "SellerProfile",
    "SellerType",
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "TestDriveBooking",
    "TestDriveStatus",
    "Transmission",
    "User",
    "Vehicle",
    "VehicleHistoryEvent",
    "detect_rollback",
]
