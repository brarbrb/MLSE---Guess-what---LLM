def test_health_endpoint(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.get_json().get("ok") is True

def test_create_user_ok(client):
    r = client.post('/api/users', json={"username": "eve", "email": "e@e", "password_hash": "h"})
    assert r.status_code in (200, 201)
    body = r.get_json()
    assert "UserID" in body
    assert body["Username"] == "eve"

def test_create_user_validation(client):
    r = client.post('/api/users', json={})
    assert r.status_code == 400
    assert r.get_json().get("error") == "username_required"
