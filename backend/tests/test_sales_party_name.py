import datetime


def _make_variant(client, headers):
    brand = client.post("/api/brands", headers=headers, json={"name": "PartyTestBrand", "code": "PTB"}).json()
    product = client.post("/api/products", headers=headers, json={"brand_id": brand["id"], "name": "Party Test Product"}).json()
    variant = client.post(
        "/api/variants",
        headers=headers,
        json={"product_id": product["id"], "sku": "PTB-TEST-1", "purchase_cost": 100, "selling_price": 150},
    ).json()
    warehouse = client.post("/api/warehouses", headers=headers, json={"name": "Party Test Warehouse", "code": "PTW"}).json()
    client.post(
        "/api/inventory/receipts",
        headers=headers,
        json={"warehouse_id": warehouse["id"], "receipt_date": "2026-08-01", "items": [{"variant_id": variant["id"], "quantity": 50, "unit_cost": 100}]},
    )
    return variant["id"], warehouse["id"]


def test_sale_with_new_party_name_creates_customer_and_returns_it(client, auth_headers):
    variant_id, warehouse_id = _make_variant(client, auth_headers)

    resp = client.post(
        "/api/sales",
        headers=auth_headers,
        json={
            "warehouse_id": warehouse_id,
            "party_name": "Ramesh Traders",
            "sale_date": "2026-08-10",
            "items": [{"variant_id": variant_id, "quantity": 2, "unit_price": 150}],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["customer_name"] == "Ramesh Traders"
    assert body["customer_id"] is not None


def test_sale_with_same_party_name_reuses_existing_customer(client, auth_headers):
    variant_id, warehouse_id = _make_variant(client, auth_headers)

    first = client.post(
        "/api/sales",
        headers=auth_headers,
        json={"warehouse_id": warehouse_id, "party_name": "Metro Footwear", "sale_date": "2026-08-11",
              "items": [{"variant_id": variant_id, "quantity": 1, "unit_price": 150}]},
    ).json()
    second = client.post(
        "/api/sales",
        headers=auth_headers,
        json={"warehouse_id": warehouse_id, "party_name": "metro footwear", "sale_date": "2026-08-12",
              "items": [{"variant_id": variant_id, "quantity": 1, "unit_price": 150}]},
    ).json()

    assert first["customer_id"] == second["customer_id"]


def test_sale_without_party_name_has_no_customer(client, auth_headers):
    variant_id, warehouse_id = _make_variant(client, auth_headers)
    resp = client.post(
        "/api/sales",
        headers=auth_headers,
        json={"warehouse_id": warehouse_id, "sale_date": "2026-08-13",
              "items": [{"variant_id": variant_id, "quantity": 1, "unit_price": 150}]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["customer_id"] is None
    assert body["customer_name"] is None


def test_list_sales_includes_party_name(client, auth_headers):
    variant_id, warehouse_id = _make_variant(client, auth_headers)
    client.post(
        "/api/sales",
        headers=auth_headers,
        json={"warehouse_id": warehouse_id, "party_name": "City Sports Store", "sale_date": "2026-08-14",
              "items": [{"variant_id": variant_id, "quantity": 1, "unit_price": 150}]},
    )
    resp = client.get("/api/sales", headers=auth_headers)
    assert resp.status_code == 200
    names = [s["customer_name"] for s in resp.json()]
    assert "City Sports Store" in names
