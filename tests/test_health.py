async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "auto48"}


async def test_listings_crud_and_pagination(client):
    # Unique make so the filtered count is immune to other modules' seeds in the
    # shared test database (every test module shares one SQLite file).
    unique_make = "Healthcomark"

    # Real flow: register (creates user + seller profile + token), then post as
    # that user — the seller is derived from the token, never sent by the client.
    reg = await client.post(
        "/v1/auth/register",
        json={
            "email": "health_seller@example.com",
            "password": "Test1234!",
            "display_name": "Health Seller",
            "seller_type": "PRIVATE",
        },
    )
    assert reg.status_code == 201, reg.text
    auth = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    listing_body = {
        "title": "2019 Healthco Corolla 1.8 Hybrid",
        "description": "One owner, full service history.",
        "price_eur_cents": 1499000,
        "mileage_km": 82000,
        "location_county": "Harjumaa",
        "vehicle": {
            "vin": "JTDBR32E720123456",
            "make": unique_make,
            "model": "Corolla",
            "variant": "1.8 Hybrid",
            "year": 2019,
            "fuel": "hybrid",
            "body": "sedan",
            "transmission": "automatic",
            "drivetrain": "fwd",
        },
    }

    # Unauthenticated create must be rejected (no anonymous posting).
    rejected = await client.post("/v1/listings", json=listing_body)
    assert rejected.status_code in (401, 403)

    created = await client.post("/v1/listings", headers=auth, json=listing_body)
    assert created.status_code == 201, created.text
    created_body = created.json()
    listing_id = created_body["id"]
    assert created_body["status"] == "draft"
    assert created_body["price_eur_cents"] == 1499000
    assert created_body["vehicle"]["make"] == unique_make

    page = await client.get("/v1/listings", params={"limit": 10, "make": unique_make})
    body = page.json()
    assert body["total"] == 1
    assert body["items"][0]["vehicle"]["make"] == unique_make

    one = await client.get(f"/v1/listings/{listing_id}")
    assert one.status_code == 200
    assert one.json()["vehicle"]["model"] == "Corolla"

    missing = await client.get("/v1/listings/999999")
    assert missing.status_code == 404
    assert missing.json()["status"] == 404
