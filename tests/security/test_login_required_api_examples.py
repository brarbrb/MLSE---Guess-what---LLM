import pytest

@pytest.mark.parametrize('path', [
    '/room/1',      # game room page (requires membership + login)
    '/menu',        # main menu requires login
])
def test_protected_pages_redirect_when_no_session(client, path):
    r = client.get(path)
    assert r.status_code in (301,302,401,403)

