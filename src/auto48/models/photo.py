"""Listing photo aggregate (ordered, optionally processed/blurred)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto48.db import Base


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    position: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    listing: Mapped["Listing"] = relationship(back_populates="photos")  # noqa: F821
