import pytest
import uuid
from backend.database.models import Game, PlayerGame


@pytest.mark.security
def test_static_directory_listing_disabled(client):
    # frameworks usually 404 or redirect; directory listing should not be shown
    r = client.get("/static/")
    if r.status_code in (301,302,404):
        assert True
    else:
        # If 200, ensure no index of listing
        assert b"Index of /static" not in r.data


@pytest.mark.parametrize('path', [
    '/room/1',      # game room page (requires membership + login)
    '/menu',        # main menu requires login
])
def test_protected_pages_redirect_when_no_session(client, path):
    r = client.get(path)
    assert r.status_code in (301,302,401,403)

@pytest.mark.security
def test_menu_requires_login_redirects(client):
    r = client.get('/menu', follow_redirects=False)
    assert r.status_code in (301, 302)

@pytest.mark.security
def test_menu_ok_when_logged_in(client, login_session):
    with login_session:
        r = client.get('/menu')
        assert r.status_code == 200


def _uniq_name(prefix="user"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _create_user_via_api(client, name=None):
    """Create a user via the public API (keeps tests realistic)."""
    uname = name or _uniq_name()
    email = f"{uname}@ok.com"
    pw = "hunter2"  # >= 6
    r = client.post("/api/users", json={"username": uname, "email": email, "password_hash": pw})
    assert r.status_code in (200, 201), r.data
    return r.get_json()["UserID"], uname

def _create_game(db_session, creator_id):
    """Create a minimal valid Game row (per your schema)."""
    g = Game(
        CreatorID=creator_id,
        GameCode=uuid.uuid4().hex[:8],  # unique 8 chars
        MaxPlayers=5,
        TotalRounds=3,
    )
    db_session.add(g)
    db_session.commit()
    db_session.refresh(g)
    return g.GameID

def _add_membership(db_session, user_id, game_id):
    pg = PlayerGame(UserID=user_id, GameID=game_id)
    db_session.add(pg)
    db_session.commit()

# UNAUTHENTICATED

@pytest.mark.security
@pytest.mark.parametrize("path", ["/profile", "/games/past", "/menu"])
def test_pages_redirect_to_login_when_unauthenticated(client, path):
    r = client.get(path, follow_redirects=False)
    # @login_required does: redirect(url_for("auth.login_get"))
    assert r.status_code in (301, 302)

@pytest.mark.security
def test_room_redirects_to_login_when_unauthenticated(client):
    # even with a numeric id, should redirect before any membership check
    r = client.get("/room/1", follow_redirects=False)
    assert r.status_code in (301, 302)


# AUTHENTICATED

@pytest.mark.security
def test_profile_ok_when_logged_in(client, login_session):
    with login_session:
        r = client.get("/profile")
        assert r.status_code == 200

@pytest.mark.security
def test_past_games_ok_when_logged_in(client, login_session):
    with login_session:
        r = client.get("/games/past")
        assert r.status_code == 200

@pytest.mark.security
def test_menu_ok_when_logged_in(client, login_session):
    with login_session:
        r = client.get("/menu")
        assert r.status_code == 200


#  AUTHENTICATED: ROOM MEMBERSHIP RULE 

@pytest.mark.security
def test_room_denies_non_member_but_logged_in(client, login_session, db_session):
    """
    Logged-in user tries to access an existing room they are NOT a member of.
    Your view should redirect to /menu (per code), not return 200.
    """
    # create another user & a game owned by that other user
    other_user_id, _ = _create_user_via_api(client, name=_uniq_name("creator"))
    game_id = _create_game(db_session, creator_id=other_user_id)

    with login_session:
        r = client.get(f"/room/{game_id}", follow_redirects=False)
        # pages.room() redirects non-members to pages.menu
        assert r.status_code in (301, 302)
        loc = r.headers.get("Location", "")
        assert "/menu" in loc


@pytest.mark.security
def test_room_allows_member_when_logged_in(client, login_session, db_session):
    """
    Logged-in user who IS a member of the room should get 200.
    """
    with login_session as user_id:
        # create a game for someone (could be same user or another)
        game_id = _create_game(db_session, creator_id=user_id)
        # add membership record for the logged-in user
        _add_membership(db_session, user_id, game_id)

        r = client.get(f"/room/{game_id}")
        assert r.status_code == 200