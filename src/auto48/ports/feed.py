"""FeedPort: clean-room protocol for fetching raw dealer inventory feeds.

Implementations live under adapters/feed/. The port keeps the domain layer
unaware of whether data comes from HTTP, a stub, or cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from auto48.models.vehicle import BodyType, Drivetrain, FuelType, Transmission


@dataclass
class ParsedListing:
    """A single normalised row extracted from a dealer feed."""

    make: str
    model: str
    year: int
    fuel: FuelType
    body: BodyType
    transmission: Transmission
    price_eur_cents: int
    title: str
    variant: str | None = None
    drivetrain: Drivetrain | None = None
    mileage_km: int | None = None
    vin: str | None = None
    plate: str | None = None
    description: str | None = None
    location_county: str | None = None


class FeedPort(Protocol):
    """Async contract for fetching raw feed bytes from a remote URL."""

    async def fetch(self, url: str) -> bytes:
        """Fetch the feed at *url* and return the raw bytes.

        Raises an appropriate exception if the fetch fails.
        """
        ...
