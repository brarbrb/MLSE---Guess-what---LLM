PRAGMA foreign_keys = ON;

-- ---------- User ----------
CREATE TABLE "User" (
  UserID INTEGER PRIMARY KEY,
  Username VARCHAR(50) UNIQUE NOT NULL,
  Email VARCHAR(255) UNIQUE NOT NULL,
  PasswordHash VARCHAR(255) NOT NULL,
  Rank VARCHAR(20) DEFAULT 'novice' CHECK (Rank IN ('novice','intermediate','expert','master')),
  TotalGamesPlayed INTEGER DEFAULT 0,
  TotalScore INTEGER DEFAULT 0,
  AvgScorePerGame REAL DEFAULT 0,
  CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  LastLogin TIMESTAMP,
  IsActive INTEGER DEFAULT 1
);

-- ---------- Game ----------
CREATE TABLE Game (
  GameID INTEGER PRIMARY KEY,
  CreatorID INTEGER NOT NULL REFERENCES "User"(UserID),
  GameCode VARCHAR(8) UNIQUE NOT NULL,
  CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  StartedAt TIMESTAMP,
  EndedAt TIMESTAMP,
  Status VARCHAR(20) DEFAULT 'waiting' CHECK (Status IN ('waiting','active','completed','cancelled')),
  MaxPlayers INTEGER NOT NULL CHECK (MaxPlayers BETWEEN 1 AND 10),
  CurrentPlayersCount INTEGER DEFAULT 1,
  TotalRounds INTEGER NOT NULL,
  CurrentRound INTEGER DEFAULT 0,
  CurrentLeaderID INTEGER REFERENCES "User"(UserID),
  WinnerID INTEGER REFERENCES "User"(UserID),
  IsPrivate INTEGER DEFAULT 0
);

-- ---------- GameSettings ----------
CREATE TABLE GameSettings (
  GameID INTEGER PRIMARY KEY REFERENCES Game(GameID),
  RoundTimeSeconds INTEGER DEFAULT 180,
  PointsCorrectGuess INTEGER DEFAULT 100,
  DifficultyLevel VARCHAR(20) DEFAULT 'medium' CHECK (DifficultyLevel IN ('easy','medium','hard')),
  AllowHints INTEGER DEFAULT 1,
  MaxHintsPerRound INTEGER DEFAULT 3
);

-- ---------- PlayerGame ----------
CREATE TABLE PlayerGame (
  PlayerGameID INTEGER PRIMARY KEY,
  UserID INTEGER NOT NULL REFERENCES "User"(UserID),
  GameID INTEGER NOT NULL REFERENCES Game(GameID),
  JoinedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PlayerFinalScore INTEGER DEFAULT 0,
  TotalCorrectGuesses INTEGER DEFAULT 0,
  TotalGuesses INTEGER DEFAULT 0,
  AverageGuessTime REAL DEFAULT 0,
  BestGuessTime REAL,
  HasWon INTEGER DEFAULT 0,
  TimesAsLeader INTEGER DEFAULT 0,
  UNIQUE(UserID, GameID)
);

-- ---------- Round ----------
CREATE TABLE Round (
  RoundID INTEGER PRIMARY KEY,
  GameID INTEGER NOT NULL REFERENCES Game(GameID),
  Participants JSON DEFAULT '[]',
  RoundNumber INTEGER NOT NULL,
  RoundWinnerID INTEGER REFERENCES "User"(UserID),
  TargetWord VARCHAR(100) NOT NULL,
  Description TEXT,
  Guesses JSON DEFAULT '[]',
  ForbiddenWords JSON NOT NULL DEFAULT '[]',
  Hints JSON,
  StartTime TIMESTAMP,                         -- nullable, no default
  EndTime TIMESTAMP,
  MaxRoundTime INTEGER DEFAULT 180,
  Status VARCHAR(20) DEFAULT 'active' CHECK (Status IN ('waiting_description','active','completed','timeout')),
  UNIQUE(GameID, RoundNumber)
);

-- ---------- Guess ----------
CREATE TABLE Guess (
  GuessID INTEGER PRIMARY KEY,
  GameID INTEGER NOT NULL REFERENCES Game(GameID),
  RoundID INTEGER NOT NULL REFERENCES Round(RoundID),
  GuesserID INTEGER NOT NULL REFERENCES "User"(UserID),
  GuessText VARCHAR(100) NOT NULL,
  GuessTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ResponseTimeSeconds REAL NOT NULL,
  PointsAwarded INTEGER DEFAULT 0,
  IsCorrect INTEGER DEFAULT 0
);

-- ---------- ChatMessage ----------
CREATE TABLE ChatMessage (
  MessageID INTEGER PRIMARY KEY,
  GameID INTEGER NOT NULL REFERENCES Game(GameID),
  RoundID INTEGER REFERENCES Round(RoundID),
  SenderID INTEGER REFERENCES "User"(UserID),
  MessageText VARCHAR(500) NOT NULL,
  MessageType VARCHAR(30) NOT NULL CHECK (MessageType IN ('guess','hint','system','general')),
  Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  IsVisible INTEGER DEFAULT 1
);
