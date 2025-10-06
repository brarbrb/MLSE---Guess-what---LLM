from backend.database.models import User
from sqlalchemy.exc import IntegrityError

def test_user_uniqueness_constraint(db_session):
    u1 = User(Username="alice", Email="alice@example.com", PasswordHash="h")
    db_session.add(u1)
    db_session.commit()

    u2 = User(Username="alice", Email="other@example.com", PasswordHash="h")
    db_session.add(u2)
    try:
        db_session.commit()
        assert False, "Expected unique constraint violation on Username"
    except IntegrityError:
        db_session.rollback()

def test_user_defaults(db_session):
    u = User(Username="bob", Email="b@b", PasswordHash="h")
    db_session.add(u)
    db_session.commit()
    assert u.Rank in ("novice","intermediate","expert","master")
    assert u.TotalGamesPlayed == 0
    assert u.TotalScore == 0
