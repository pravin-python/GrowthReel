def test_health_is_public_and_minimal(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_has_security_headers(client):
    response = client.get("/api/v1/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    assert "X-Request-ID" in response.headers


def test_health_detailed_requires_auth(client):
    response = client.get("/api/v1/health/detailed")

    assert response.status_code == 401


def test_health_detailed_never_leaks_internals(client, auth_headers):
    response = client.get("/api/v1/health/detailed", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert set(body.keys()) == {"database", "cache", "version"}
