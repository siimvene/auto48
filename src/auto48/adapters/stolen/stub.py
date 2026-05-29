"""StubStolenVehicleAdapter: deterministic offline adapter for dev and tests.

A VIN is flagged as stolen if it appears in a small hardcoded denylist OR if
it ends with the suffix "STOLEN" (case-insensitive after normalisation).
All other VINs are considered clean.  Source is always "stub".
"""

from __future__ import annotations

from typing import Final

from auto48.ports.stolen import StolenCheckResult

# Hardcoded demo denylist — representative of what a real registry would hold.
_DENYLIST: Final[frozenset[str]] = frozenset(
    {
        "WBA3A5G5XEF000001",
        "JT2BF22K1W0071053",
        "1HGBH41JXMN109186",
    }
)

# Suffix rule: any VIN ending with this string (uppercased) is flagged.
_FLAGGED_SUFFIX: Final[str] = "STOLEN"


class StubStolenVehicleAdapter:
    """Deterministic stub adapter — no network calls, safe for offline dev and CI."""

    async def check(self, vin: str) -> StolenCheckResult:
        """Return flagged=True for denylist VINs or VINs ending in 'STOLEN'.

        Args:
            vin: The Vehicle Identification Number to check (normalised to uppercase).

        Returns:
            :class:`StolenCheckResult` with flagged status and source "stub".
        """
        normalised = vin.upper().strip()
        in_denylist = normalised in _DENYLIST
        suffix_match = normalised.endswith(_FLAGGED_SUFFIX)

        flagged = in_denylist or suffix_match

        detail: str | None
        if in_denylist:
            detail = "VIN appears in demo stolen-vehicle denylist."
        elif suffix_match:
            detail = "VIN matches deterministic stolen-vehicle rule (suffix)."
        else:
            detail = None

        return StolenCheckResult(
            vin=normalised,
            flagged=flagged,
            source="stub",
            detail=detail,
        )
