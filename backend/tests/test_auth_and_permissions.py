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


def test_change_password_requires_correct_current_password(client, auth_headers):
    resp = client.post(
        "/api/auth/change-password",
        headers=auth_headers,
        json={"current_password": "wrong", "new_password": "NewPassword123"},
    )
    assert resp.status_code == 400


def test_change_password_rejects_same_password(client, auth_headers):
    resp = client.post(
        "/api/auth/change-password",
        headers=auth_headers,
        json={"current_password": "ChangeMe123!", "new_password": "ChangeMe123!"},
    )
    assert resp.status_code == 400


def test_change_password_succeeds_and_new_password_works(client, auth_headers):
    resp = client.post(
        "/api/auth/change-password",
        headers=auth_headers,
        json={"current_password": "ChangeMe123!", "new_password": "BrandNewPassword456"},
    )
    assert resp.status_code == 200, resp.text

    # Old password no longer works.
    old_login = client.post("/api/auth/login", json={"email": "admin@shoexpress.co.in", "password": "ChangeMe123!"})
    assert old_login.status_code == 401

    # New password does.
    new_login = client.post("/api/auth/login", json={"email": "admin@shoexpress.co.in", "password": "BrandNewPassword456"})
    assert new_login.status_code == 200


def test_change_password_rejects_too_short_new_password(client, auth_headers):
    resp = client.post(
        "/api/auth/change-password",
        headers=auth_headers,
        json={"current_password": "ChangeMe123!", "new_password": "short"},
    )
    assert resp.status_code == 422
