#!/usr/bin/env python3
"""Seed the LOCAL dev database with sellers + ACTIVE car listings via the ORM.

Self-contained (no HTTP, no manual SQL): creates the schema, wipes existing
listings/vehicles, and inserts a deterministic demo set so the marketplace loop
(browse / search / detail / valuation) works end-to-end.

    python scripts/seed_dev.py        # uses AUTO48_DATABASE_URL or ./auto48.db

Dev only — gated on environment == "local".
"""

import asyncio

from sqlalchemy import delete, select

from auto48.config import get_settings
from auto48.db import Base, async_session_factory, engine
from auto48.models.listing import Listing, ListingStatus
from auto48.models.photo import Photo
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User
from auto48.models.vehicle import BodyType, Drivetrain, FuelType, Transmission, Vehicle

_GEO = {
    "Harjumaa": (59.437, 24.754),
    "Tartumaa": (58.378, 26.729),
    "Pärnumaa": (58.386, 24.497),
    "Ida-Virumaa": (59.356, 27.412),
    "Lääne-Virumaa": (59.346, 26.356),
}

# email, display_name, type
_SELLERS = [
    ("sales@autobaltic.ee", "Auto Baltic OÜ", SellerType.DEALER, "Auto Baltic OÜ"),
    ("jaan.tamm@example.ee", "Jaan Tamm", SellerType.PRIVATE, None),
]

# title, desc, make, model, variant, year, fuel, body, transmission, drivetrain,
# price_cents, mileage, county, seller_index
_LISTINGS = [
    ("Volkswagen Golf 2.0 TDI", "Hooldusraamat olemas, suverehvid komplektis. Üks omanik.",
     "Volkswagen", "Golf", "2.0 TDI Comfortline", 2018, "diesel", "hatchback", "manual", "fwd", 1_490_000, 142_000, "Harjumaa", 0),
    ("Toyota RAV4 2.5 Hybrid AWD", "Tehasegarantii kehtib. Adaptiivne püsikiirushoidik, soojendusega istmed.",
     "Toyota", "RAV4", "2.5 Hybrid AWD-i", 2020, "hybrid", "suv", "automatic", "awd", 3_250_000, 68_000, "Tartumaa", 0),
    ("Škoda Octavia Combi 2.0 TDI", "Ökonoomne universaal, värske hooldus. Veokonks, talvirehvid eraldi.",
     "Škoda", "Octavia", "Combi 2.0 TDI Style", 2017, "diesel", "wagon", "manual", "fwd", 1_290_000, 198_000, "Pärnumaa", 0),
    ("BMW 320d Sedan", "M-sport pakett, nahksisu. Tehniliselt korras, hiljuti vahetatud rihm.",
     "BMW", "320d", "320d M Sport", 2016, "diesel", "sedan", "automatic", "rwd", 1_650_000, 210_000, "Harjumaa", 1),
    ("Audi A4 Avant 2.0 TDI quattro", "Quattro nelikvedu, virtuaalne armatuur, LED-tuled.",
     "Audi", "A4", "Avant 2.0 TDI quattro S line", 2019, "diesel", "wagon", "semi_automatic", "awd", 2_490_000, 120_000, "Tartumaa", 0),
    ("Tesla Model 3 Standard Range+", "Üks omanik, garaažiauto. Autopilot, tasuta tarkvarauuendused.",
     "Tesla", "Model 3", "Standard Range Plus", 2021, "electric", "sedan", "automatic", "rwd", 3_390_000, 45_000, "Harjumaa", 1),
    ("Volvo XC60 D4 AWD", "Turvaline pereauto, Pilot Assist. Talve- ja suverehvid valuvelgedel.",
     "Volvo", "XC60", "D4 AWD Momentum", 2018, "diesel", "suv", "automatic", "awd", 2_750_000, 135_000, "Harjumaa", 0),
    ("Nissan Qashqai 1.6 Bensiin", "Soodne ja töökindel linnamaastur. Uued piduriklotsid.",
     "Nissan", "Qashqai", "1.6 Acenta", 2015, "petrol", "suv", "manual", "fwd", 1_190_000, 156_000, "Ida-Virumaa", 1),
    ("Kia Ceed SW 1.4 T-GDI", "Tehasegarantii 7 aastat. Üks omanik, väike läbisõit.",
     "Kia", "Ceed", "SW 1.4 T-GDI EX", 2019, "petrol", "wagon", "manual", "fwd", 1_540_000, 88_000, "Lääne-Virumaa", 0),
    ("Mercedes-Benz E220d", "AMG-pakett, õhkvedrustus, panoraamkatus. Täielik hooldusajalugu.",
     "Mercedes-Benz", "E220d", "E220d AMG Line", 2017, "diesel", "sedan", "automatic", "rwd", 2_190_000, 175_000, "Harjumaa", 1),
    # --- Comparable cluster: VW Golf 2018 at a price spread so the valuation /
    #     deal-score feature has >=3 comps and visibly resolves (great→high). ---
    ("Volkswagen Golf 1.6 TDI Trendline", "Soodne ja säästlik. Korralik linnaauto.",
     "Volkswagen", "Golf", "1.6 TDI Trendline", 2018, "diesel", "hatchback", "manual", "fwd", 1_190_000, 168_000, "Tartumaa", 1),
    ("Volkswagen Golf 1.5 TSI Highline", "Hooldatud esinduses, LED-tuled, navi.",
     "Volkswagen", "Golf", "1.5 TSI Highline", 2018, "petrol", "hatchback", "automatic", "fwd", 1_590_000, 96_000, "Harjumaa", 0),
    ("Volkswagen Golf 2.0 TDI R-Line", "Tippvarustus, virtuaalne armatuur, soojendusega rool.",
     "Volkswagen", "Golf", "2.0 TDI R-Line", 2018, "diesel", "hatchback", "semi_automatic", "fwd", 1_790_000, 110_000, "Harjumaa", 0),
]


async def _get_or_create_seller(session, email, display_name, stype, company):
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name=display_name)
        session.add(user)
        await session.flush()
    profile = await session.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if profile is None:
        profile = SellerProfile(user_id=user.id, type=stype, company_name=company, verified=False)
        session.add(profile)
        await session.flush()
    return profile.id


async def main() -> None:
    settings = get_settings()
    if settings.environment != "local":
        raise SystemExit(f"Refusing to seed: environment={settings.environment!r} (local only)")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # Clean slate for the demo dataset (dev only).
        await session.execute(delete(Photo))
        await session.execute(delete(Listing))
        await session.execute(delete(Vehicle))
        await session.flush()

        seller_ids = [
            await _get_or_create_seller(session, *s) for s in _SELLERS
        ]

        count = 0
        for row in _LISTINGS:
            (title, desc, make, model, variant, year, fuel, body, trans, drive,
             price, mileage, county, sidx) = row
            lat, lon = _GEO[county]
            vehicle = Vehicle(
                make=make, model=model, variant=variant, year=year,
                fuel=FuelType(fuel), body=BodyType(body),
                transmission=Transmission(trans), drivetrain=Drivetrain(drive),
            )
            session.add(vehicle)
            await session.flush()
            listing = Listing(
                seller_id=seller_ids[sidx % len(seller_ids)],
                vehicle_id=vehicle.id,
                title=title,
                description=desc,
                price_eur_cents=price,
                mileage_km=mileage,
                location_county=county,
                lat=lat,
                lon=lon,
                status=ListingStatus.ACTIVE,
            )
            session.add(listing)
            count += 1

        await session.commit()
        print(f"Seeded {len(seller_ids)} sellers and {count} ACTIVE listings.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
