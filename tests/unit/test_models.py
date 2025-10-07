import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from backend.database.models import (
    User, Game, GameSettings, PlayerGame, Round, Guess, ChatMessage
)

# tests for the database models and constraints
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


#  User / basic constraints 
def test_user_rank_check_constraint(db_session):
    u = User(Username="r1", Email="r1@e.com", PasswordHash="x", Rank="expert")
    db_session.add(u); db_session.commit()  # valid value passes

    bad = User(Username="bad_rank", Email="bad_rank@e.com", PasswordHash="x", Rank="legendary")
    db_session.add(bad)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_user_created_at_autoset(db_session):
    u = User(Username="ts1", Email="ts1@e.com", PasswordHash="x")
    db_session.add(u); db_session.commit()
    assert isinstance(u.CreatedAt, datetime)
    # LastLogin is nullable by default
    assert u.LastLogin is None
    assert u.IsActive is True


#  Game constraints 
@pytest.mark.parametrize("status", ["waiting","active","completed","cancelled"])
def test_game_status_allowed_values(db_session, status):
    creator = User(Username=f"g_{status}", Email=f"g_{status}@e.com", PasswordHash="x")
    db_session.add(creator); db_session.commit()

    g = Game(
        CreatorID=creator.UserID,
        GameCode=f"C{status[:2].upper()}001",
        MaxPlayers=5,
        TotalRounds=3,
        Status=status,
    )
    db_session.add(g); db_session.commit()
    assert g.Status == status

def test_game_status_invalid_rejected(db_session):
    creator = User(Username="gx", Email="gx@e.com", PasswordHash="x")
    db_session.add(creator); db_session.commit()
    g = Game(CreatorID=creator.UserID, GameCode="BAD001", MaxPlayers=5, TotalRounds=3, Status="bogus")
    db_session.add(g)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

@pytest.mark.parametrize("max_players, ok", [(1, True), (10, True), (0, False), (11, False)])
def test_game_maxplayers_bounds(db_session, max_players, ok):
    creator = User(Username=f"mp_{max_players}", Email=f"mp_{max_players}@e.com", PasswordHash="x")
    db_session.add(creator); db_session.commit()
    g = Game(CreatorID=creator.UserID, GameCode=f"M{max_players:02d}", MaxPlayers=max_players, TotalRounds=2)
    db_session.add(g)
    if ok:
        db_session.commit()
        assert g.MaxPlayers == max_players
    else:
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

def test_game_has_settings_1to1(db_session):
    u = User(Username="gs_u", Email="gs_u@e.com", PasswordHash="x")
    db_session.add(u); db_session.commit()
    g = Game(CreatorID=u.UserID, GameCode="GS0001", MaxPlayers=4, TotalRounds=3)
    db_session.add(g); db_session.commit()
    s = GameSettings(GameID=g.GameID, RoundTimeSeconds=120, DifficultyLevel="hard", AllowHints=False)
    db_session.add(s); db_session.commit()
    # relationship backref
    assert g.settings.RoundTimeSeconds == 120
    assert s.game.GameID == g.GameID

def test_game_cascade_deletes_children(db_session):
    u = User(Username="casc_u", Email="casc_u@e.com", PasswordHash="x")
    db_session.add(u); db_session.commit()
    g = Game(CreatorID=u.UserID, GameCode="CA0001", MaxPlayers=4, TotalRounds=2)
    db_session.add(g); db_session.commit()

    # attach children
    s = GameSettings(GameID=g.GameID)
    db_session.add(s)

    r1 = Round(GameID=g.GameID, RoundNumber=1, TargetWord="apple", TargetWordNorm="apple")
    r2 = Round(GameID=g.GameID, RoundNumber=2, TargetWord="pear", TargetWordNorm="pear")
    db_session.add_all([r1, r2]); db_session.commit()

    # chat message attached to game
    m = ChatMessage(GameID=g.GameID, RoundID=None, SenderID=None, MessageText="hi", MessageType="system")
    db_session.add(m); db_session.commit()

    # player relation
    pg = PlayerGame(UserID=u.UserID, GameID=g.GameID)
    db_session.add(pg); db_session.commit()

    # delete parent and assert cascades
    db_session.delete(g); db_session.commit()

    # ensure rows are gone
    assert db_session.get(Game, g.GameID) is None
    assert db_session.get(GameSettings, g.GameID) is None
    assert db_session.query(Round).filter_by(GameID=g.GameID).count() == 0
    assert db_session.query(PlayerGame).filter_by(GameID=g.GameID).count() == 0
    assert db_session.query(ChatMessage).filter_by(GameID=g.GameID).count() == 0


#  PlayerGame constraints 

def test_playergame_unique_user_per_game(db_session):
    u = User(Username="pg_u", Email="pg_u@e.com", PasswordHash="x")
    v = User(Username="pg_v", Email="pg_v@e.com", PasswordHash="x")
    db_session.add_all([u, v]); db_session.commit()
    g = Game(CreatorID=u.UserID, GameCode="PG0001", MaxPlayers=4, TotalRounds=2)
    db_session.add(g); db_session.commit()

    pg1 = PlayerGame(UserID=u.UserID, GameID=g.GameID)
    db_session.add(pg1); db_session.commit()

    pg_dup = PlayerGame(UserID=u.UserID, GameID=g.GameID)
    db_session.add(pg_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


#  Round constraints 

def test_round_unique_per_game(db_session):
    u = User(Username="rd_u", Email="rd_u@e.com", PasswordHash="x")
    db_session.add(u); db_session.commit()
    g = Game(CreatorID=u.UserID, GameCode="RD0001", MaxPlayers=4, TotalRounds=2)
    db_session.add(g); db_session.commit()

    r1 = Round(GameID=g.GameID, RoundNumber=1, TargetWord="cat", TargetWordNorm="cat")
    db_session.add(r1); db_session.commit()

    r_dup = Round(GameID=g.GameID, RoundNumber=1, TargetWord="dog", TargetWordNorm="dog")
    db_session.add(r_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_round_status_check_constraint(db_session):
    u = User(Username="rs_u", Email="rs_u@e.com", PasswordHash="x")
    db_session.add(u); db_session.commit()
    g = Game(CreatorID=u.UserID, GameCode="RS0001", MaxPlayers=4, TotalRounds=1)
    db_session.add(g); db_session.commit()

    ok = Round(GameID=g.GameID, RoundNumber=1, TargetWord="tree", TargetWordNorm="tree", Status="active")
    db_session.add(ok); db_session.commit()

    bad = Round(GameID=g.GameID, RoundNumber=2, TargetWord="x", TargetWordNorm="x", Status="invalid_status")
    db_session.add(bad)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_round_json_defaults_are_independent(db_session):
    u = User(Username="j_u", Email="j_u@e.com", PasswordHash="x")
    db_session.add(u); db_session.commit()
    g = Game(CreatorID=u.UserID, GameCode="JS0001", MaxPlayers=4, TotalRounds=2)
    db_session.add(g); db_session.commit()

    r1 = Round(GameID=g.GameID, RoundNumber=1, TargetWord="sun", TargetWordNorm="sun")
    r2 = Round(GameID=g.GameID, RoundNumber=2, TargetWord="moon", TargetWordNorm="moon")
    db_session.add_all([r1, r2]); db_session.commit()

    # mutate r1's lists
    r1.Participants.append(1)
    r1.Guesses.append({"t":"hi"})
    r1.ForbiddenWords.append("blue")
    db_session.commit()

    # r2 should remain untouched (no shared default objects)
    assert r2.Participants == []
    assert r2.Guesses == []
    assert r2.ForbiddenWords == []


#  Guess / ChatMessage basics

def test_guess_defaults_and_relationships(db_session):
    u = User(Username="gu_u", Email="gu_u@e.com", PasswordHash="x")
    db_session.add(u); db_session.commit()
    g = Game(CreatorID=u.UserID, GameCode="GU0001", MaxPlayers=4, TotalRounds=1)
    db_session.add(g); db_session.commit()
    r = Round(GameID=g.GameID, RoundNumber=1, TargetWord="bee", TargetWordNorm="bee")
    db_session.add(r); db_session.commit()

    guess = Guess(GameID=g.GameID, RoundID=r.RoundID, GuesserID=u.UserID, GuessText="honey", ResponseTimeSeconds=1.2)
    db_session.add(guess); db_session.commit()
    assert guess.IsCorrect is False
    assert guess.PointsAwarded == 0
    assert any(x.GuessID == guess.GuessID for x in r.guesses)

def test_chatmessage_type_check_constraint(db_session):
    u = User(Username="cmu", Email="cmu@e.com", PasswordHash="x")
    db_session.add(u); db_session.commit()
    g = Game(CreatorID=u.UserID, GameCode="CM0001", MaxPlayers=4, TotalRounds=1)
    db_session.add(g); db_session.commit()

    ok = ChatMessage(GameID=g.GameID, RoundID=None, SenderID=u.UserID,
                     MessageText="hello", MessageType="general")
    db_session.add(ok); db_session.commit()

    bad = ChatMessage(GameID=g.GameID, RoundID=None, SenderID=u.UserID,
                      MessageText="oops", MessageType="not_allowed")
    db_session.add(bad)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()