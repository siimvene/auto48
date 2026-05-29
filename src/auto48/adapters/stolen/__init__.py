"""Stolen-vehicle adapter factory.

Always returns StubStolenVehicleAdapter for now; a real registry adapter can
be wired here once the external source is available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from auto48.config import Settings
    from auto48.ports.stolen import StolenVehiclePort


def get_stolen_adapter(settings: Settings) -> StolenVehiclePort:
    """Return the appropriate StolenVehiclePort implementation.

    Currently always returns the deterministic stub.  Wire a real adapter here
    once an external registry source is available.

    Args:
        settings: Application settings (reserved for future real-adapter config).

    Returns:
        A :class:`StolenVehiclePort` implementation.
    """
    from auto48.adapters.stolen.stub import StubStolenVehicleAdapter

    return StubStolenVehicleAdapter()
