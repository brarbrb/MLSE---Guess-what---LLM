from datetime import datetime
from sqlalchemy import (
    Integer, String, Text, ForeignKey, DateTime, Boolean, CheckConstraint,
    UniqueConstraint, Column
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from .db import Base

# ---------- User ----------
class User(Base):
    __tablename__ = "User"
    UserID: Mapped[int] = mapped_column(Integer, primary_key=True)
    Username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    Email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    PasswordHash: Mapped[str] = mapped_column(String(255), nullable=False)
    Rank: Mapped[str] = mapped_column(String(20), default="novice")
    TotalGamesPlayed: Mapped[int] = mapped_column(Integer, default=0)
    TotalScore: Mapped[int] = mapped_column(Integer, default=0)
    AvgScorePerGame: Mapped[float] = mapped_column(default=0.0)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    LastLogin: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    IsActive: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint("Rank IN ('novice','intermediate','expert','master')"),
    )

# ---------- Game ----------
class Game(Base):
    __tablename__ = "Game"
    GameID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CreatorID: Mapped[int] = mapped_column(ForeignKey("User.UserID"), nullable=False)
    GameCode: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    StartedAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    EndedAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Status: Mapped[str] = mapped_column(String(20), default="waiting")
    MaxPlayers: Mapped[int] = mapped_column(Integer, nullable=False)
    CurrentPlayersCount: Mapped[int] = mapped_column(Integer, default=1)
    TotalRounds: Mapped[int] = mapped_column(Integer, nullable=False)
    CurrentRound: Mapped[int] = mapped_column(Integer, default=0)
    CurrentLeaderID: Mapped[int | None] = mapped_column(ForeignKey("User.UserID"))
    WinnerID: Mapped[int | None] = mapped_column(ForeignKey("User.UserID"))
    IsPrivate: Mapped[bool] = mapped_column(Boolean, default=False)


    __table_args__ = (
        CheckConstraint("Status IN ('waiting','active','completed','cancelled')"),
        CheckConstraint("MaxPlayers BETWEEN 1 AND 10"),
    )

    creator = relationship("User", foreign_keys=[CreatorID])
    rounds = relationship("Round", back_populates="game", cascade="all, delete-orphan")
    players = relationship("PlayerGame", back_populates="game", cascade="all, delete-orphan")
    settings = relationship("GameSettings", back_populates="game", uselist=False, cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", cascade="all, delete-orphan", backref="game")

# ---------- GameSettings (1:1 with Game) ----------
class GameSettings(Base):
    __tablename__ = "GameSettings"
    GameID: Mapped[int] = mapped_column(ForeignKey("Game.GameID"), primary_key=True)
    RoundTimeSeconds: Mapped[int] = mapped_column(Integer, default=180)
    PointsCorrectGuess: Mapped[int] = mapped_column(Integer, default=100)
    DifficultyLevel: Mapped[str] = mapped_column(String(20), default="medium")
    AllowHints: Mapped[bool] = mapped_column(Boolean, default=True)
    MaxHintsPerRound: Mapped[int] = mapped_column(Integer, default=3)

    __table_args__ = (
        CheckConstraint("DifficultyLevel IN ('easy','medium','hard')"),
    )

    game = relationship("Game", back_populates="settings")

# ---------- PlayerGame (many-to-many) ----------
class PlayerGame(Base):
    __tablename__ = "PlayerGame"
    PlayerGameID: Mapped[int] = mapped_column(Integer, primary_key=True)
    UserID: Mapped[int] = mapped_column(ForeignKey("User.UserID"), nullable=False)
    GameID: Mapped[int] = mapped_column(ForeignKey("Game.GameID"), nullable=False)
    JoinedAt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    PlayerFinalScore: Mapped[int] = mapped_column(Integer, default=0)
    TotalCorrectGuesses: Mapped[int] = mapped_column(Integer, default=0)
    TotalGuesses: Mapped[int] = mapped_column(Integer, default=0)
    AverageGuessTime: Mapped[float] = mapped_column(default=0.0)
    BestGuessTime: Mapped[float | None] = mapped_column(nullable=True)
    HasWon: Mapped[bool] = mapped_column(Boolean, default=False)
    TimesAsLeader: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("UserID", "GameID"),)

    user = relationship("User")
    game = relationship("Game", back_populates="players")

# ---------- Round ----------
class Round(Base):
    __tablename__ = "Round"
    RoundID: Mapped[int] = mapped_column(Integer, primary_key=True)
    GameID: Mapped[int] = mapped_column(ForeignKey("Game.GameID"), nullable=False)
    # Stored as JSON in SQLite (TEXT + JSON1)
    Participants: Mapped[list] = mapped_column("Participants", JSON, default=list)
    RoundNumber: Mapped[int] = mapped_column(Integer, nullable=False)
    RoundWinnerID: Mapped[int | None] = mapped_column(ForeignKey("User.UserID"), nullable=True, default=None)
    TargetWord: Mapped[str] = mapped_column(String(100), nullable=False)
    Description: Mapped[str | None] = mapped_column(Text, nullable=True)
    Guesses: Mapped[list] = mapped_column(JSON, default=list)
    ForbiddenWords: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    Hints: Mapped[list | None] = mapped_column(JSON, nullable=True)
    StartTime: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    EndTime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    MaxRoundTime: Mapped[int] = mapped_column(Integer, default=180)
    Status: Mapped[str] = mapped_column(String(20), default="active")

    __table_args__ = (
        UniqueConstraint("GameID", "RoundNumber"),
        CheckConstraint("Status IN ('waiting_description','active','completed','timeout')"),
    )

    game = relationship("Game", back_populates="rounds")
    guesses = relationship("Guess", cascade="all, delete-orphan", backref="round")


# ---------- Guess ----------
class Guess(Base):
    __tablename__ = "Guess"
    GuessID: Mapped[int] = mapped_column(Integer, primary_key=True)
    GameID: Mapped[int] = mapped_column(ForeignKey("Game.GameID"), nullable=False)
    RoundID: Mapped[int] = mapped_column(ForeignKey("Round.RoundID"), nullable=False)
    GuesserID: Mapped[int] = mapped_column(ForeignKey("User.UserID"), nullable=False)
    GuessText: Mapped[str] = mapped_column(String(100), nullable=False)
    GuessTime: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ResponseTimeSeconds: Mapped[float] = mapped_column(nullable=False)
    PointsAwarded: Mapped[int] = mapped_column(Integer, default=0)
    # In your DDL: IsCorrect BOOLEAN DEFAULT 0 (moved below to keep standards)
    IsCorrect: Mapped[bool] = mapped_column(Boolean, default=False)

# ---------- ChatMessage ----------
class ChatMessage(Base):
    __tablename__ = "ChatMessage"
    MessageID: Mapped[int] = mapped_column(Integer, primary_key=True)
    GameID: Mapped[int] = mapped_column(ForeignKey("Game.GameID"), nullable=False)
    RoundID: Mapped[int | None] = mapped_column(ForeignKey("Round.RoundID"), nullable=True)
    SenderID: Mapped[int | None] = mapped_column(ForeignKey("User.UserID"), nullable=True)
    MessageText: Mapped[str] = mapped_column(String(500), nullable=False)
    MessageType: Mapped[str] = mapped_column(String(30), nullable=False)
    Timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    IsVisible: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint("MessageType IN ('guess','hint','system','general')"),
    )
