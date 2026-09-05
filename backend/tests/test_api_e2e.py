"""End-to-end simulation mirroring the manual QA pass: create a product,
create a SKU, receive inventory, sell inventory, return inventory, adjust
inventory, set a deadline, view aging, run forecasting, generate a purchase
recommendation, export a report. Every step calls the real API through
FastAPI's TestClient — nothing here mocks the service layer."""


def test_full_business_workflow(client, auth_headers):
    h = auth_headers

    brand = client.post("/api/brands", headers=h, json={"name": "E2E Brand", "code": "E2EB"}).json()

    category = client.post("/api/categories", headers=h, json={"name": "E2E Category"}).json()

    product = client.post(
        "/api/products",
        headers=h,
        json={"brand_id": brand["id"], "category_id": category["id"], "name": "E2E Product"},
    ).json()

    variant = client.post(
        "/api/variants",
        headers=h,
        json={
            "product_id": product["id"],
            "sku": "E2EB-PROD-9",
            "size": "9",
            "purchase_cost": 1000,
            "selling_price": 1500,
            "minimum_order_quantity": 10,
        },
    ).json()

    warehouse = client.post("/api/warehouses", headers=h, json={"name": "E2E Warehouse", "code": "E2EW"}).json()

    receipt_resp = client.post(
        "/api/inventory/receipts",
        headers=h,
        json={
            "warehouse_id": warehouse["id"],
            "receipt_date": "2026-08-01",
            "items": [{"variant_id": variant["id"], "quantity": 100, "unit_cost": 1000}],
        },
    )
    assert receipt_resp.status_code == 201, receipt_resp.text

    stock = client.get(f"/api/variants/{variant['id']}", headers=h).json()
    assert stock["current_stock"] == 100

    sale_resp = client.post(
        "/api/sales",
        headers=h,
        json={
            "warehouse_id": warehouse["id"],
            "sale_date": "2026-08-05",
            "items": [{"variant_id": variant["id"], "quantity": 10, "unit_price": 1500}],
        },
    )
    assert sale_resp.status_code == 201, sale_resp.text
    sale = sale_resp.json()

    stock = client.get(f"/api/variants/{variant['id']}", headers=h).json()
    assert stock["current_stock"] == 90

    return_resp = client.post(
        "/api/sales/returns",
        headers=h,
        json={"sale_item_id": sale["items"][0]["id"], "quantity": 2, "notes": "wrong size"},
    )
    assert return_resp.status_code == 201, return_resp.text
    stock = client.get(f"/api/variants/{variant['id']}", headers=h).json()
    assert stock["current_stock"] == 92

    adjust_resp = client.post(
        "/api/inventory/adjustments",
        headers=h,
        json={"variant_id": variant["id"], "warehouse_id": warehouse["id"], "quantity": 5, "direction": "OUT", "notes": "damaged"},
    )
    assert adjust_resp.status_code == 201, adjust_resp.text
    stock = client.get(f"/api/variants/{variant['id']}", headers=h).json()
    assert stock["current_stock"] == 87

    # Oversell must be rejected, not silently allowed.
    oversell = client.post(
        "/api/sales",
        headers=h,
        json={"warehouse_id": warehouse["id"], "sale_date": "2026-08-06", "items": [{"variant_id": variant["id"], "quantity": 9999, "unit_price": 1500}]},
    )
    assert oversell.status_code == 400

    deadline_resp = client.post(
        "/api/deadlines",
        headers=h,
        json={"scope_type": "SKU", "scope_id": variant["id"], "deadline_date": "2026-12-31", "warning_days": 14, "notes": "clear stock"},
    )
    assert deadline_resp.status_code == 201, deadline_resp.text

    aging_resp = client.get("/api/inventory/aging/summary", headers=h)
    assert aging_resp.status_code == 200
    assert sum(row["quantity"] for row in aging_resp.json()) >= 87

    forecast_resp = client.get(f"/api/forecasting/{variant['id']}", headers=h)
    assert forecast_resp.status_code == 200
    forecast = forecast_resp.json()
    assert forecast["confidence"] in ("LOW", "MEDIUM", "HIGH")
    assert "explanation" in forecast and len(forecast["explanation"]) > 0

    rec_gen = client.post("/api/recommendations/generate", headers=h)
    assert rec_gen.status_code == 200
    recs = client.get("/api/recommendations", headers=h).json()
    assert any(r["sku"] == "E2EB-PROD-9" for r in recs)

    export_resp = client.get("/api/reports/inventory/export?format=csv", headers=h)
    assert export_resp.status_code == 200
    assert b"E2EB-PROD-9" in export_resp.content

    audit_resp = client.get(f"/api/audit-logs?entity_type=product_variant&entity_id={variant['id']}", headers=h)
    assert audit_resp.status_code == 200
    actions = {entry["action"] for entry in audit_resp.json()}
    assert "CREATE" in actions
    assert "STOCK_ADJUSTMENT" in actions
