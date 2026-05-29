"""StolenVehiclePort: clean-room protocol for stolen-vehicle check providers.

Implementations live under adapters/stolen/. The port keeps the domain layer
unaware of whether the source is an Interpol-style registry, a national database,
or a deterministic stub.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class StolenCheckResult:
    """Result of a stolen-vehicle check for a given VIN."""

    vin: str
    flagged: bool
    source: str
    detail: str | None = None


class StolenVehiclePort(Protocol):
    """Async contract for stolen-vehicle check providers."""

    async def check(self, vin: str) -> StolenCheckResult:
        """Return the stolen-vehicle check result for the given VIN.

        Args:
            vin: The Vehicle Identification Number to check.

        Returns:
            :class:`StolenCheckResult` with flagged status and source info.
        """
        ...
