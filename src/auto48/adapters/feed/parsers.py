"""Feed parsers: transform raw CSV or JSON bytes into a list of ParsedListing.

Only stdlib (csv, json) is used — no third-party parsing libraries.
Invalid rows are silently skipped (logged at WARNING) so the caller's
error_count comes from downstream persistence failures, not parse failures.
A separate bad-row counter is returned alongside the parsed list so the service
can initialise error_count before attempting DB writes.
"""

from __future__ import annotations

import csv
import io
import json
import logging

from auto48.models.vehicle import BodyType, Drivetrain, FuelType, Transmission
from auto48.ports.feed import ParsedListing

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FUEL_MAP: dict[str, FuelType] = {m.value: m for m in FuelType}
_BODY_MAP: dict[str, BodyType] = {m.value: m for m in BodyType}
_TX_MAP: dict[str, Transmission] = {m.value: m for m in Transmission}
_DT_MAP: dict[str, Drivetrain] = {m.value: m for m in Drivetrain}


def _parse_row(row: dict[str, object]) -> ParsedListing | None:
    """Convert a dict-row to ParsedListing; return None if required fields are invalid."""

    def _str(key: str) -> str | None:
        v = row.get(key)
        return str(v).strip() if v is not None and str(v).strip() else None

    def _int(key: str) -> int | None:
        v = row.get(key)
        if v is None:
            return None
        try:
            return int(str(v))
        except (ValueError, TypeError):
            return None

    # Required string fields
    make = _str("make")
    model = _str("model")
    title = _str("title")
    if not make or not model or not title:
        logger.warning("Skipping row: missing make/model/title in %r", row)
        return None

    # Required int fields
    year = _int("year")
    price_eur_cents = _int("price_eur_cents")
    if year is None or price_eur_cents is None:
        logger.warning("Skipping row: missing year/price_eur_cents in %r", row)
        return None

    # Required enum fields
    fuel_raw = _str("fuel")
    body_raw = _str("body")
    tx_raw = _str("transmission")

    fuel = _FUEL_MAP.get(fuel_raw or "")
    body = _BODY_MAP.get(body_raw or "")
    transmission = _TX_MAP.get(tx_raw or "")

    if fuel is None or body is None or transmission is None:
        logger.warning("Skipping row: invalid enum value in %r", row)
        return None

    # Optional fields
    drivetrain_raw = _str("drivetrain")
    drivetrain = _DT_MAP.get(drivetrain_raw or "") if drivetrain_raw else None

    return ParsedListing(
        make=make,
        model=model,
        year=year,
        fuel=fuel,
        body=body,
        transmission=transmission,
        price_eur_cents=price_eur_cents,
        title=title,
        variant=_str("variant"),
        drivetrain=drivetrain,
        mileage_km=_int("mileage_km"),
        vin=_str("vin"),
        plate=_str("plate"),
        description=_str("description"),
        location_county=_str("location_county"),
    )


# ---------------------------------------------------------------------------
# Public parse functions
# ---------------------------------------------------------------------------


def parse_csv(data: bytes) -> tuple[list[ParsedListing], int]:
    """Parse *data* (UTF-8 CSV with a header row) into ParsedListing objects.

    Returns ``(listings, skipped_count)`` where *skipped_count* is the number
    of rows that failed validation.
    """
    text = data.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    listings: list[ParsedListing] = []
    skipped = 0
    for raw_row in reader:
        # csv.DictReader yields dict[str, str]; cast to dict[str, object] for _parse_row
        row: dict[str, object] = dict(raw_row)
        result = _parse_row(row)
        if result is None:
            skipped += 1
        else:
            listings.append(result)
    return listings, skipped


def parse_json(data: bytes) -> tuple[list[ParsedListing], int]:
    """Parse *data* (UTF-8 JSON array of objects) into ParsedListing objects.

    Returns ``(listings, skipped_count)`` where *skipped_count* is the number
    of rows that failed validation.
    """
    try:
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON feed: %s", exc)
        return [], 0

    if not isinstance(payload, list):
        logger.error("JSON feed root must be an array; got %s", type(payload).__name__)
        return [], 0

    listings: list[ParsedListing] = []
    skipped = 0
    for item in payload:
        if not isinstance(item, dict):
            skipped += 1
            continue
        row: dict[str, object] = item
        result = _parse_row(row)
        if result is None:
            skipped += 1
        else:
            listings.append(result)
    return listings, skipped
