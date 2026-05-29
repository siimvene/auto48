#!/usr/bin/env python3
"""Seed the auto48 backend with mock sellers + car adverts via the HTTP API.

Run ON the server (talks to the local API):
    python3 seed-mock-listings.py [base_url]   # default http://127.0.0.1:8000

Idempotent-ish: re-running adds another batch. Listings are created (DRAFT) then
the caller flips them to 'active' via SQL. Estonian market data.
"""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

# Approx county-seat coordinates.
GEO = {
    "Harjumaa": (59.437, 24.754),
    "Tartumaa": (58.378, 26.729),
    "Pärnumaa": (58.386, 24.497),
    "Ida-Virumaa": (59.356, 27.412),
    "Lääne-Virumaa": (59.346, 26.356),
}

SELLERS = [
    {"email": "sales@autobaltic.ee", "password": "Test1234!", "display_name": "Auto Baltic OÜ", "seller_type": "DEALER"},
    {"email": "jaan.tamm@example.ee", "password": "Test1234!", "display_name": "Jaan Tamm", "seller_type": "PRIVATE"},
]

# (title, desc, make, model, variant, year, fuel, body, transmission, drivetrain,
#  price_eur_cents, mileage_km, county, seller_index)
LISTINGS = [
    ("Volkswagen Golf 2.0 TDI", "Hooldusraamat olemas, suverehvid komplektis. Üks omanik, mittesuitsetaja.",
     "Volkswagen", "Golf", "2.0 TDI Comfortline", 2018, "diesel", "hatchback", "manual", "fwd", 1_490_000, 142_000, "Harjumaa", 0),
    ("Toyota RAV4 2.5 Hybrid AWD", "Tehasегарантii kehtib. Adaptiivne püsikiirushoidik, soojendusega istmed.",
     "Toyota", "RAV4", "2.5 Hybrid AWD-i", 2020, "hybrid", "suv", "automatic", "awd", 3_250_000, 68_000, "Tartumaa", 0),
    ("Škoda Octavia Combi 2.0 TDI", "Ökonoomne universaal, värske hooldus. Veokonks, talvirehvid eraldi.",
     "Škoda", "Octavia", "Combi 2.0 TDI Style", 2017, "diesel", "wagon", "manual", "fwd", 1_290_000, 198_000, "Pärnumaa", 0),
    ("BMW 320d Sedan", "M-sport pakett, nahksisu. Tehniliselt korras, hiljuti vahetatud rihm.",
     "BMW", "320d", "320d M Sport", 2016, "diesel", "sedan", "automatic", "rwd", 1_650_000, 210_000, "Harjumaa", 1),
    ("Audi A4 Avant 2.0 TDI quattro", "Quattro nelikvedu, virtuaalne armatuur, LED-tuled. Hooldatud esinduses.",
     "Audi", "A4", "Avant 2.0 TDI quattro S line", 2019, "diesel", "wagon", "semi_automatic", "awd", 2_490_000, 120_000, "Tartumaa", 0),
    ("Tesla Model 3 Standard Range+", "Üks omanik, garaažiauto. Autopilot, tasuta tarkvarauuendused.",
     "Tesla", "Model 3", "Standard Range Plus", 2021, "electric", "sedan", "automatic", "rwd", 3_390_000, 45_000, "Harjumaa", 1),
    ("Volvo XC60 D4 AWD", "Turvaline pereauto, Pilot Assist. Talve- ja suverehvid valuvelgedel.",
     "Volvo", "XC60", "D4 AWD Momentum", 2018, "diesel", "suv", "automatic", "awd", 2_750_000, 135_000, "Harjumaa", 0),
    ("Nissan Qashqai 1.6 Bensiin", "Soodne ja töökindel linnamaastur. Uued piduriklotsid ja õli vahetatud.",
     "Nissan", "Qashqai", "1.6 Acenta", 2015, "petrol", "suv", "manual", "fwd", 1_190_000, 156_000, "Ida-Virumaa", 1),
    ("Kia Ceed SW 1.4 T-GDI", "Tehasegarantii 7 aastat. Üks omanik, väike läbisõit, suurepärases korras.",
     "Kia", "Ceed", "SW 1.4 T-GDI EX", 2019, "petrol", "wagon", "manual", "fwd", 1_540_000, 88_000, "Lääne-Virumaa", 0),
    ("Mercedes-Benz E220d", "AMG-pakett, õhkvedrustus, panoraamkatus. Täielik hooldusajalugu.",
     "Mercedes-Benz", "E220d", "E220d AMG Line", 2017, "diesel", "sedan", "automatic", "rwd", 2_190_000, 175_000, "Harjumaa", 1),
]


def post(path, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    seller_ids = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else []
    if not seller_ids:
        print("Pass seller ids as args 2..N (resolved from the DB).", file=sys.stderr)
        sys.exit(2)
    print(f"Seller ids: {seller_ids}")

    created = 0
    for t in LISTINGS:
        (title, desc, make, model, variant, year, fuel, body, trans, drive,
         price, mileage, county, sidx) = t
        lat, lon = GEO[county]
        payload = {
            "seller_id": seller_ids[sidx % len(seller_ids)],
            "title": title,
            "description": desc,
            "price_eur_cents": price,
            "mileage_km": mileage,
            "location_county": county,
            "lat": lat,
            "lon": lon,
            "vehicle": {
                "make": make, "model": model, "variant": variant, "year": year,
                "fuel": fuel, "body": body, "transmission": trans, "drivetrain": drive,
            },
        }
        code, resp = post("/v1/listings", payload)
        if code == 201:
            created += 1
            print(f"  ✓ [{resp['id']}] {title} — {price//100}€")
        else:
            print(f"  ✗ {title}: HTTP {code} {resp}")
    print(f"Created {created}/{len(LISTINGS)} listings.")


if __name__ == "__main__":
    main()
