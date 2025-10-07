def test_malformed_json_returns_4xx_not_500(client):
    r = client.post('/api/users', data='{"username": "a"', headers={"Content-Type": "application/json"})
    assert r.status_code in (400, 422)

def test_wrong_content_type_returns_4xx(client):
    r = client.post('/api/users', data="username=alice&email=a@b.com&password_hash=h", headers={"Content-Type": "text/plain"})
    assert r.status_code in (400, 415, 422)

def test_missing_content_type_treated_as_4xx(client):
    r = client.post('/api/users', data='{"username":"a"}')  # no header
    assert r.status_code in (400, 422)
