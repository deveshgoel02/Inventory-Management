def _make_variant(client, headers):
    brand = client.post("/api/brands", headers=headers, json={"name": "AllotTestBrand", "code": "ATB"}).json()
    product = client.post("/api/products", headers=headers, json={"brand_id": brand["id"], "name": "Allot Test Product"}).json()
    variant = client.post(
        "/api/variants",
        headers=headers,
        json={"product_id": product["id"], "sku": "ATB-TEST-1", "purchase_cost": 100, "selling_price": 150},
    ).json()
    warehouse = client.post("/api/warehouses", headers=headers, json={"name": "Allot Test Warehouse", "code": "ATW"}).json()
    client.post(
        "/api/inventory/receipts",
        headers=headers,
        json={"warehouse_id": warehouse["id"], "receipt_date": "2026-08-01", "items": [{"variant_id": variant["id"], "quantity": 100, "unit_cost": 100}]},
    )
    return variant["id"], warehouse["id"]


def _make_salesman(client, headers, email="salesman1@shoexpress.co.in", role_name="INVENTORY_STAFF"):
    roles = client.get("/api/roles", headers=headers).json()
    role_id = next(r["id"] for r in roles if r["name"] == role_name)
    user = client.post(
        "/api/users",
        headers=headers,
        json={"email": email, "full_name": "Test Salesman", "password": "SalesPass123!", "role_id": role_id},
    ).json()
    login = client.post("/api/auth/login", json={"email": email, "password": "SalesPass123!"})
    token = login.json()["access_token"]
    return user["id"], {"Authorization": f"Bearer {token}"}


def test_create_allotment_and_partial_execution(client, auth_headers):
    variant_id, warehouse_id = _make_variant(client, auth_headers)
    salesman_id, salesman_headers = _make_salesman(client, auth_headers)

    resp = client.post(
        "/api/allotments",
        headers=auth_headers,
        json={
            "salesman_id": salesman_id,
            "variant_id": variant_id,
            "warehouse_id": warehouse_id,
            "allotted_quantity": 10,
            "allotted_date": "2026-08-05",
        },
    )
    assert resp.status_code == 201, resp.text
    allotment = resp.json()
    assert allotment["executed_quantity"] == 0
    assert allotment["fulfillment_status"] == "PENDING"

    client.post(
        "/api/sales",
        headers=salesman_headers,
        json={
            "warehouse_id": warehouse_id,
            "sale_date": "2026-08-10",
            "items": [{"variant_id": variant_id, "quantity": 4, "unit_price": 150}],
        },
    )

    detail = client.get(f"/api/allotments/{allotment['id']}", headers=auth_headers).json()
    assert detail["executed_quantity"] == 4
    assert detail["remaining_quantity"] == 6
    assert detail["completion_pct"] == 40.0
    assert detail["fulfillment_status"] == "IN_PROGRESS"
    assert len(detail["contributing_sales"]) == 1
    assert detail["contributing_sales"][0]["quantity"] == 4


def test_allotment_fulfilled_when_target_met(client, auth_headers):
    variant_id, warehouse_id = _make_variant(client, auth_headers)
    salesman_id, salesman_headers = _make_salesman(client, auth_headers, email="salesman2@shoexpress.co.in")

    allotment = client.post(
        "/api/allotments",
        headers=auth_headers,
        json={"salesman_id": salesman_id, "variant_id": variant_id, "allotted_quantity": 5, "allotted_date": "2026-08-05"},
    ).json()

    client.post(
        "/api/sales",
        headers=salesman_headers,
        json={"warehouse_id": warehouse_id, "sale_date": "2026-08-06", "items": [{"variant_id": variant_id, "quantity": 5, "unit_price": 150}]},
    )

    detail = client.get(f"/api/allotments/{allotment['id']}", headers=auth_headers).json()
    assert detail["fulfillment_status"] == "FULFILLED"
    assert detail["remaining_quantity"] == 0


def test_sales_by_a_different_salesman_do_not_count(client, auth_headers):
    variant_id, warehouse_id = _make_variant(client, auth_headers)
    salesman_id, _ = _make_salesman(client, auth_headers, email="salesman3@shoexpress.co.in")
    _, other_headers = _make_salesman(client, auth_headers, email="salesman4@shoexpress.co.in")

    allotment = client.post(
        "/api/allotments",
        headers=auth_headers,
        json={"salesman_id": salesman_id, "variant_id": variant_id, "allotted_quantity": 5, "allotted_date": "2026-08-05"},
    ).json()

    client.post(
        "/api/sales",
        headers=other_headers,
        json={"warehouse_id": warehouse_id, "sale_date": "2026-08-06", "items": [{"variant_id": variant_id, "quantity": 5, "unit_price": 150}]},
    )

    detail = client.get(f"/api/allotments/{allotment['id']}", headers=auth_headers).json()
    assert detail["executed_quantity"] == 0
    assert detail["fulfillment_status"] == "PENDING"


def test_salesman_without_manage_permission_cannot_create_allotment(client, auth_headers):
    variant_id, _ = _make_variant(client, auth_headers)
    salesman_id, salesman_headers = _make_salesman(client, auth_headers, email="salesman5@shoexpress.co.in")

    resp = client.post(
        "/api/allotments",
        headers=salesman_headers,
        json={"salesman_id": salesman_id, "variant_id": variant_id, "allotted_quantity": 5, "allotted_date": "2026-08-05"},
    )
    assert resp.status_code == 403


def test_salesman_can_view_allotments(client, auth_headers):
    variant_id, _ = _make_variant(client, auth_headers)
    salesman_id, salesman_headers = _make_salesman(client, auth_headers, email="salesman6@shoexpress.co.in")
    client.post(
        "/api/allotments",
        headers=auth_headers,
        json={"salesman_id": salesman_id, "variant_id": variant_id, "allotted_quantity": 5, "allotted_date": "2026-08-05"},
    )
    resp = client.get("/api/allotments", headers=salesman_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_cancel_allotment(client, auth_headers):
    variant_id, _ = _make_variant(client, auth_headers)
    salesman_id, _ = _make_salesman(client, auth_headers, email="salesman7@shoexpress.co.in")
    allotment = client.post(
        "/api/allotments",
        headers=auth_headers,
        json={"salesman_id": salesman_id, "variant_id": variant_id, "allotted_quantity": 5, "allotted_date": "2026-08-05"},
    ).json()

    resp = client.patch(f"/api/allotments/{allotment['id']}", headers=auth_headers, json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["fulfillment_status"] == "CANCELLED"
