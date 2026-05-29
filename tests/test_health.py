async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "auto48"}


async def test_listings_crud_and_pagination(client, seller_id):
    created = await client.post(
        "/v1/listings",
        json={
            "seller_id": seller_id,
            "title": "2019 Toyota Corolla 1.8 Hybrid",
            "description": "One owner, full service history.",
            "price_eur_cents": 1499000,
            "mileage_km": 82000,
            "location_county": "Harjumaa",
            "vehicle": {
                "vin": "JTDBR32E720123456",
                "make": "Toyota",
                "model": "Corolla",
                "variant": "1.8 Hybrid",
                "year": 2019,
                "fuel": "hybrid",
                "body": "sedan",
                "transmission": "automatic",
                "drivetrain": "fwd",
            },
        },
    )
    assert created.status_code == 201
    created_body = created.json()
    listing_id = created_body["id"]
    assert created_body["status"] == "draft"
    assert created_body["price_eur_cents"] == 1499000
    assert created_body["vehicle"]["make"] == "Toyota"

    page = await client.get("/v1/listings", params={"limit": 10, "make": "Toyota"})
    body = page.json()
    assert body["total"] == 1
    assert body["items"][0]["vehicle"]["make"] == "Toyota"

    one = await client.get(f"/v1/listings/{listing_id}")
    assert one.status_code == 200
    assert one.json()["vehicle"]["model"] == "Corolla"

    missing = await client.get("/v1/listings/999999")
    assert missing.status_code == 404
    assert missing.json()["status"] == 404
