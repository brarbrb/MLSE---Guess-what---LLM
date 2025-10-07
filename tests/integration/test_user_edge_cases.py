import pytest
import uuid

def _uniq():
    x = uuid.uuid4().hex[:8]
    return f"user_{x}", f"{x}@e.com", "hunter2"

def test_create_user_minimal_payload(client):
    uname, email, pw = _uniq()
    r = client.post('/api/users', json={"username": uname, "email": email, "password_hash": pw})
    assert r.status_code in (200, 201)
    body = r.get_json()
    assert body["Username"] == uname
    assert "UserID" in body

def test_create_user_rejects_duplicate_username(client):
    uname, email, pw = _uniq()
    r1 = client.post('/api/users', json={"username": uname, "email": email, "password_hash": pw})
    assert r1.status_code in (200, 201)
    # same username 
    r2 = client.post('/api/users', json={"username": uname, "email": f"new_{email}", "password_hash": pw})
    assert r2.status_code in (400, 409)

def test_create_user_rejects_duplicate_email(client):
    uname, email, pw = _uniq()
    r1 = client.post('/api/users', json={"username": uname, "email": email, "password_hash": pw})
    assert r1.status_code in (200, 201)
    # different username, same email
    r2 = client.post('/api/users', json={"username": f"{uname}_2", "email": email, "password_hash": pw})
    assert r2.status_code in (400, 409)

def test_create_user_strips_whitespace(client):
    uname, email, pw = _uniq()
    r = client.post('/api/users', json={"username": f"  {uname}  ", "email": f"  {email}  ", "password_hash": pw})
    assert r.status_code in (200, 201)
    body = r.get_json()
    assert body["Username"] == uname  # server should trim or normalize

# different cases table
@pytest.mark.parametrize("payload", [
    {},  # empty
    {"username": ""},  # missing fields
    {"username": "x"*256, "email": "a@b.com", "password_hash": "hunter2"},  # too long username
    {"username": "weird🧪", "email": "bad-format", "password_hash": "hunter2"},  # bad email format
    {"username": "cululu", "email": "cccc@t.com", "password_hash": "h"},  # short password (<6)
    {"username": "okuser", "email": "no-suffix@domain.org", "password_hash": "hunter2"},  # must end with .com
])
def test_create_user_validation_errors(client, payload):
    r = client.post('/api/users', json=payload)
    # Accept any client error status; never 5xx
    assert r.status_code in (400, 422, 409)

# all characters allowed should succeed 
def test_create_user_all_chars_allowed(client):
    uname = "sql_inj🙂 <>\"' ;-- DROP TABLE user;/* */"
    email = f"{uuid.uuid4().hex[:6]}+tag@anything.com"  # must end with .com
    pw = "p@$$w0rd🙂--okay"  # >= 6, any chars allowed
    r = client.post('/api/users', json={"username": uname, "email": email, "password_hash": pw})
    assert r.status_code in (200, 201)

# too long password 
def test_password_too_long(client):
    uname, email, _ = _uniq()
    long_pw = "a" * 129
    r = client.post('/api/users', json={"username": uname, "email": email, "password_hash": long_pw})
    assert r.status_code == 422

#  too long email
def test_email_too_long(client):
    uname, _, pw = _uniq()
    local = "a" * 200
    domain = "b" * 60  
    email = f"{local}@{domain}.com"  # >255 total
    r = client.post('/api/users', json={"username": uname, "email": email, "password_hash": pw})
    assert r.status_code == 422

# username boundary 
def test_username_boundary(client):
    email = f"{uuid.uuid4().hex[:6]}@ok.com"
    pw = "hunter2"
    uname_ok = "x" * 50
    uname_bad = "x" * 51

    r_ok = client.post('/api/users', json={"username": uname_ok, "email": email, "password_hash": pw})
    assert r_ok.status_code in (200, 201)

    email2 = f"{uuid.uuid4().hex[:6]}@ok.com"
    r_bad = client.post('/api/users', json={"username": uname_bad, "email": email2, "password_hash": pw})
    assert r_bad.status_code == 422


def test_health_endpoint(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.get_json().get("ok") is True

def test_email_uniqueness_case_insensitive(client):
    uname, email, pw = _uniq()
    r1 = client.post('/api/users', json={"username": uname, "email": email, "password_hash": pw})
    assert r1.status_code in (200, 201)
    # same email, different case 
    r2 = client.post('/api/users', json={"username": f"{uname}_2", "email": email.upper(), "password_hash": pw})
    assert r2.status_code in (400, 409, 422)  # never 2xx

def test_idempotent_retry_same_payload_gives_conflict(client):
    uname, email, pw = _uniq()
    payload = {"username": uname, "email": email, "password_hash": pw}
    r1 = client.post('/api/users', json=payload); assert r1.status_code in (200, 201)
    r2 = client.post('/api/users', json=payload)
    assert r2.status_code in (400, 409)  # duplicate replay should not create a second user