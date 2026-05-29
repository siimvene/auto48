"""Natural-language search service for listings.

Rule-based, bilingual (Estonian / English) query parser.
NO LLM or external dependencies — pure regex + lookup tables.

Contract:
  parse_query(text) -> ParsedQuery   (pure, no I/O)
  run(db, text, *, limit, offset) -> (ParsedQuery, list[Listing], int)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from auto48.models.listing import Listing, ListingStatus
from auto48.models.vehicle import BodyType, FuelType, Transmission
from auto48.services.search import (
    build_count_query,
    build_filters,
    build_listing_query,
)

# ──────────────────────────────────────────────────────────────────────────────
# 1.  LOOKUP TABLES
# ──────────────────────────────────────────────────────────────────────────────

#: Canonical casing used for the facet value.
_KNOWN_MAKES: list[str] = [
    "Volkswagen",
    "Toyota",
    "BMW",
    "Audi",
    "Mercedes-Benz",
    "Mercedes",
    "Škoda",
    "Skoda",
    "Volvo",
    "Tesla",
    "Nissan",
    "Kia",
    "Hyundai",
    "Opel",
    "Ford",
    "Renault",
    "Peugeot",
    "Citroën",
    "Citroen",
    "Honda",
    "Mazda",
    "Subaru",
    "Mitsubishi",
    "Suzuki",
    "Seat",
    "Fiat",
    "Alfa",
    "Lexus",
    "Porsche",
    "Land Rover",
    "Jeep",
    "Chevrolet",
    "Dodge",
    "Chrysler",
    "Cadillac",
    "Buick",
    "Infiniti",
    "Acura",
    "Genesis",
    "Lada",
    "Dacia",
    "Smart",
    "Mini",
    "Bentley",
    "Rolls-Royce",
    "Lamborghini",
    "Ferrari",
    "Maserati",
    "Jaguar",
    "Aston Martin",
]

# Case-insensitive token → BodyType
_BODY_KEYWORDS: dict[str, BodyType] = {
    "universaal": BodyType.WAGON,
    "estate": BodyType.WAGON,
    "wagon": BodyType.WAGON,
    "maastur": BodyType.SUV,
    "suv": BodyType.SUV,
    "linnamaastur": BodyType.SUV,
    "sedaan": BodyType.SEDAN,
    "sedan": BodyType.SEDAN,
    "luukpära": BodyType.HATCHBACK,
    "luukpara": BodyType.HATCHBACK,
    "hatchback": BodyType.HATCHBACK,
    "kupee": BodyType.COUPE,
    "coupe": BodyType.COUPE,
    "kabriolett": BodyType.CONVERTIBLE,
    "convertible": BodyType.CONVERTIBLE,
    "kaubik": BodyType.VAN,
    "van": BodyType.VAN,
    "pikap": BodyType.PICKUP,
    "pickup": BodyType.PICKUP,
    "mahtuniversaal": BodyType.MINIVAN,
    "minivan": BodyType.MINIVAN,
}

# Case-insensitive token → FuelType
_FUEL_KEYWORDS: dict[str, FuelType] = {
    "diisel": FuelType.DIESEL,
    "diesel": FuelType.DIESEL,
    "bensiin": FuelType.PETROL,
    "petrol": FuelType.PETROL,
    "bensa": FuelType.PETROL,
    "elekter": FuelType.ELECTRIC,
    "electric": FuelType.ELECTRIC,
    "ev": FuelType.ELECTRIC,
    "hübriid": FuelType.HYBRID,
    "hubriid": FuelType.HYBRID,
    "hybrid": FuelType.HYBRID,
    "pistik": FuelType.PLUGIN_HYBRID,
    "plug-in": FuelType.PLUGIN_HYBRID,
    "phev": FuelType.PLUGIN_HYBRID,
    "gaas": FuelType.LPG,
    "lpg": FuelType.LPG,
}

# Case-insensitive token → Transmission
_TRANSMISSION_KEYWORDS: dict[str, Transmission] = {
    "automaat": Transmission.AUTOMATIC,
    "automatic": Transmission.AUTOMATIC,
    "manuaal": Transmission.MANUAL,
    "manual": Transmission.MANUAL,
    "käsi": Transmission.MANUAL,
    "kasi": Transmission.MANUAL,
}

# ──────────────────────────────────────────────────────────────────────────────
# 2.  DATACLASS
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class ParsedQuery:
    """Facets extracted from a natural-language query string."""

    make: str | None = field(default=None)
    model: str | None = field(default=None)
    fuel: FuelType | None = field(default=None)
    body: BodyType | None = field(default=None)
    transmission: Transmission | None = field(default=None)
    year_min: int | None = field(default=None)
    year_max: int | None = field(default=None)
    price_max_eur_cents: int | None = field(default=None)
    price_min_eur_cents: int | None = field(default=None)
    mileage_max: int | None = field(default=None)


# ──────────────────────────────────────────────────────────────────────────────
# 3.  HELPERS — each is a pure extractor
# ──────────────────────────────────────────────────────────────────────────────

def _extract_make(text_lower: str, text_orig: str) -> str | None:
    """Return the first recognised make (canonical casing) or None."""
    for make in _KNOWN_MAKES:
        pattern = re.compile(r"\b" + re.escape(make.lower()) + r"\b")
        if pattern.search(text_lower):
            return make
    return None


def _extract_body(text_lower: str) -> BodyType | None:
    """Return the first matching body-type keyword or None."""
    # Sort by descending length so "mahtuniversaal" matches before "universaal".
    for kw in sorted(_BODY_KEYWORDS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
            return _BODY_KEYWORDS[kw]
    return None


def _extract_fuel(text_lower: str) -> FuelType | None:
    """Return the first matching fuel-type keyword or None."""
    for kw in sorted(_FUEL_KEYWORDS, key=len, reverse=True):
        # plug-in contains a hyphen so we can't use \b on both sides uniformly
        pattern = r"(?<![a-zäöüõ])" + re.escape(kw) + r"(?![a-zäöüõ])"
        if re.search(pattern, text_lower):
            return _FUEL_KEYWORDS[kw]
    return None


def _extract_transmission(text_lower: str) -> Transmission | None:
    """Return the first matching transmission keyword or None."""
    for kw in sorted(_TRANSMISSION_KEYWORDS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
            return _TRANSMISSION_KEYWORDS[kw]
    return None


# Patterns for numeric values — grouped digits first to avoid partial matches.
_NUM_RE = re.compile(
    r"""
    (?:
        (\d{1,3}(?:\s\d{3})+)   # "10 000" — space-grouped thousands
        |(\d+)                   # bare integer
    )
    """,
    re.VERBOSE,
)

# Currency hint words / symbols that follow the number.
_CURRENCY_HINTS = re.compile(
    r"(?:€|eur(?:o[st]?)?|tuhat|t\b|k\b)",
    re.IGNORECASE,
)

# "k" suffix attached to the digit token (e.g. "10k").
_K_SUFFIX = re.compile(r"^(\d+)k$", re.IGNORECASE)


def _parse_number(raw: str) -> int:
    """Parse a raw numeric string (may contain a space-thousand-separator) to int."""
    return int(raw.replace(" ", ""))


def _extract_price_and_year(
    text_lower: str,
) -> tuple[int | None, int | None, int | None, int | None]:
    """Return (price_max, price_min, year_min, year_max) from the text.

    Disambiguation rule:
      - Explicit currency indicator (€/eur/eurot/k/tuhat) after the number → price.
      - Else number in [1900, 2099] → year.
      - Else → price.
    A 4-digit bare year token (no keyword) → year_min by default.
    """
    price_max: int | None = None
    price_min: int | None = None
    year_min: int | None = None
    year_max: int | None = None

    # Work on the original-lower text.
    # We scan for price/year keywords followed by a number.

    # --- MAX patterns (kuni / under / max / <=) ---
    _max_prefix = re.compile(
        r"""(?:kuni|under|max|<=)\s*""",
        re.IGNORECASE | re.VERBOSE,
    )
    # --- MIN patterns (alates / from / over / uuem kui) ---
    _min_prefix = re.compile(
        r"""(?:alates|from|over|uuem\s+kui)\s*""",
        re.IGNORECASE | re.VERBOSE,
    )

    def _classify_number_at(pos: int, num_val: int, text: str) -> str:
        """Return 'price' or 'year' based on context after pos."""
        # Look ahead up to 8 chars for currency hints.
        lookahead = text[pos : pos + 12]
        # Also check for 'k' suffix on the raw token preceding.
        if _CURRENCY_HINTS.search(lookahead):
            return "price"
        # year range
        if 1900 <= num_val <= 2099:
            return "year"
        return "price"

    def _to_cents(num_val: int, text_after: str) -> int:
        """Convert numeric value to EUR cents, handling k/tuhat multipliers."""
        after = text_after[:12].strip()
        if re.match(r"^(?:tuhat|t\b)", after, re.IGNORECASE):
            return num_val * 1000 * 100
        if re.match(r"^k\b", after, re.IGNORECASE):
            return num_val * 1000 * 100
        return num_val * 100

    # Scan with prefix keywords first.
    for m_prefix, mode in [
        (_max_prefix, "max"),
        (_min_prefix, "min"),
    ]:
        for prefix_match in m_prefix.finditer(text_lower):
            rest = text_lower[prefix_match.end() :]
            m_num = _NUM_RE.match(rest)
            if not m_num:
                continue
            raw = (m_num.group(1) or m_num.group(2) or "").strip()
            num_val = _parse_number(raw)
            after_num = rest[m_num.end() :]
            kind = _classify_number_at(0, num_val, after_num)
            if kind == "price":
                cents = _to_cents(num_val, after_num)
                if mode == "max":
                    price_max = cents
                else:
                    price_min = cents
            else:  # year
                if mode == "max":
                    year_max = num_val
                else:
                    year_min = num_val

    # Bare 4-digit years (no keyword).  Only if no year already set.
    for m in re.finditer(r"\b((?:19|20)\d{2})\b", text_lower):
        val = int(m.group(1))
        if year_min is None and year_max is None:
            year_min = val

    return price_max, price_min, year_min, year_max


def _extract_standalone_price(text_lower: str) -> tuple[int | None, int | None]:
    """Extract bare '<number>[k/tuhat/€/eur]' tokens as price hints (fallback).

    Used only when no keyword prefix was found and no year was found.
    Returns (price_max, price_min) — both None if not found.
    """
    # e.g. "10k", "10000", "10 000 eur"  with no directional prefix
    # We scan all "Nk" tokens.
    for m in re.finditer(r"\b(\d+)k\b", text_lower):
        val = int(m.group(1)) * 1000 * 100
        return val, None
    return None, None


# ──────────────────────────────────────────────────────────────────────────────
# 4.  PUBLIC PARSER
# ──────────────────────────────────────────────────────────────────────────────


def parse_query(text: str) -> ParsedQuery:
    """Parse a bilingual (ET/EN) natural-language query into structured facets.

    Only sets a facet on a confident match; conservative by design.
    """
    text_lower = text.lower()

    make = _extract_make(text_lower, text)
    body = _extract_body(text_lower)
    fuel = _extract_fuel(text_lower)
    transmission = _extract_transmission(text_lower)

    price_max, price_min, year_min, year_max = _extract_price_and_year(text_lower)

    return ParsedQuery(
        make=make,
        body=body,
        fuel=fuel,
        transmission=transmission,
        year_min=year_min,
        year_max=year_max,
        price_max_eur_cents=price_max,
        price_min_eur_cents=price_min,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 5.  ASYNC RUNNER
# ──────────────────────────────────────────────────────────────────────────────


async def run(
    db: AsyncSession,
    text: str,
    *,
    limit: int,
    offset: int,
) -> tuple[ParsedQuery, list[Listing], int]:
    """Parse *text* and return (parsed_query, listings, total) over ACTIVE listings."""
    pq = parse_query(text)

    filters = build_filters(
        make=pq.make,
        model=pq.model,
        year_min=pq.year_min,
        year_max=pq.year_max,
        price_min=pq.price_min_eur_cents,
        price_max=pq.price_max_eur_cents,
        mileage_max=pq.mileage_max,
        fuel=pq.fuel,
        body=pq.body,
        transmission=pq.transmission,
        status=ListingStatus.ACTIVE,
    )

    total = (await db.scalar(build_count_query(filters))) or 0
    rows = (
        await db.scalars(build_listing_query(filters, "newest", limit, offset))
    ).all()

    return pq, list(rows), total
