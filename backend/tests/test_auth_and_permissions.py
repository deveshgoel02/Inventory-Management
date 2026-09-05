def test_login_rejects_wrong_password(client):
    resp = client.post("/api/auth/login", json={"email": "admin@shoexpress.co.in", "password": "wrong"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_admin_permissions(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"]["name"] == "ADMIN"
    assert "user:manage" in body["permissions"]


def test_viewer_role_cannot_create_products(client, auth_headers, db_session):
    from app.auth.security import hash_password
    from app.models.auth import Role, User

    viewer_role = db_session.query(Role).filter(Role.name == "VIEWER").one()
    viewer = User(email="viewer@shoexpress.co.in", full_name="Viewer User", hashed_password=hash_password("pw123456"), role_id=viewer_role.id)
    db_session.add(viewer)
    db_session.commit()

    login = client.post("/api/auth/login", json={"email": "viewer@shoexpress.co.in", "password": "pw123456"})
    assert login.status_code == 200
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.post(
        "/api/products",
        headers=viewer_headers,
        json={"brand_id": 1, "name": "Should Not Be Created"},
    )
    assert resp.status_code == 403
