def test_e2e_create_user_then_open_menu(client, login_session):
    # Create user + set session (login)
    with login_session:
        # Visit landing then menu
        r1 = client.get('/')
        assert r1.status_code in (200, 302)  # root may redirect to /menu
        r2 = client.get('/menu')
        assert r2.status_code == 200
