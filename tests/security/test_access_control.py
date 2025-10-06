def test_menu_requires_login_redirects(client):
    # Should redirect unauthenticated users to login page
    r = client.get('/menu', follow_redirects=False)
    assert r.status_code in (301,302)

def test_menu_ok_when_logged_in(client, login_session):
    with login_session:
        r = client.get('/menu')
        assert r.status_code == 200
