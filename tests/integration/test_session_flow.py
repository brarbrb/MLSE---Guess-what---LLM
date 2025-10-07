def test_get_on_post_only_returns_405_or_404(client):
    r = client.get('/api/users')  
    assert r.status_code in (404, 405)  # never 500

def test_unsupported_method_returns_405_or_404(client):
    r = client.put('/api/health')
    assert r.status_code in (404, 405)

def test_can_view_menu_with_session(client, login_session):
    with login_session:
        r = client.get('/menu')          
        assert r.status_code == 200
