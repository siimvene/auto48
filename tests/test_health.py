async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "auto48"}


async def test_listings_crud_and_pagination(client):
    created = await client.post(
        "/v1/listings",
        json={
            "make": "Toyota",
            "model": "Corolla",
            "year": 2019,
            "price_eur": 14990,
            "mileage_km": 82000,
        },
    )
    assert created.status_code == 201
    listing_id = created.json()["id"]

    page = await client.get("/v1/listings", params={"limit": 10})
    body = page.json()
    assert body["total"] == 1
    assert body["items"][0]["make"] == "Toyota"

    one = await client.get(f"/v1/listings/{listing_id}")
    assert one.status_code == 200

    missing = await client.get("/v1/listings/999999")
    assert missing.status_code == 404
    assert missing.json()["status"] == 404
