"""SavedSearch and Alert ORM aggregates.

SavedSearch — a user-defined facet-query that can trigger email alerts.
Alert       — a record linking a saved search to a matched listing (idempotent).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto48.db import Base

if TYPE_CHECKING:
    from auto48.models.listing import Listing
    from auto48.models.user import User


class SavedSearch(Base):
    """A named facet-query owned by a user that drives periodic alert emails."""

    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    # Facet params stored as JSON: make/model/year_min/year_max/price_min/
    # price_max/fuel/body/transmission/location (all optional, nullable values
    # kept as None so build_filters can handle them directly).
    query: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship()
    alerts: Mapped[list[Alert]] = relationship(back_populates="saved_search")


class Alert(Base):
    """Records that a saved search matched a specific listing (sent or pending)."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    saved_search_id: Mapped[int] = mapped_column(
        ForeignKey("saved_searches.id"), index=True
    )
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    saved_search: Mapped[SavedSearch] = relationship(back_populates="alerts")
    listing: Mapped[Listing] = relationship()
