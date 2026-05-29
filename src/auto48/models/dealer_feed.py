"""DealerFeed and IngestRun ORM aggregates for dealer inventory feed ingestion."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto48.db import Base

if TYPE_CHECKING:
    pass


def _enum_values(e: type[enum.Enum]) -> list[str]:
    return [m.value for m in e]


class FeedFormat(enum.Enum):
    CSV = "csv"
    JSON = "json"


class IngestStatus(enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class DealerFeed(Base):
    __tablename__ = "dealer_feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("seller_profiles.id"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    format: Mapped[FeedFormat] = mapped_column(
        Enum(FeedFormat, name="feed_format", values_callable=_enum_values)
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    runs: Mapped[list[IngestRun]] = relationship(
        back_populates="feed", order_by="IngestRun.started_at"
    )


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("dealer_feeds.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    status: Mapped[IngestStatus] = mapped_column(
        Enum(IngestStatus, name="ingest_status", values_callable=_enum_values),
        default=IngestStatus.RUNNING,
    )
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    feed: Mapped[DealerFeed] = relationship(back_populates="runs")
