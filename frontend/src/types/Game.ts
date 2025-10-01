export enum GameStatus {
  WAITING = "waiting",
  ACTIVE = "active",
  COMPLETED = "completed",
  CANCELLED = "cancelled",
}


interface GameArgs {
  gameId: number;
  creatorId: number;
  createdAt: Date | string;
  startedAt?: Date | string | null;
  endedAt?: Date | string | null;
  status?: GameStatus;

  maxPlayers?: number;
  roundTimeSeconds?: number;
}

export class Game {
  gameId: number;
  creatorId: number;
  createdAt: Date;
  startedAt: Date | null;
  endedAt: Date | null;
  status: GameStatus;

  maxPlayers: number;
  roundTimeSeconds: number;

  constructor({
                gameId,
                creatorId,
                createdAt,
                startedAt = null,
                endedAt = null,
                status = GameStatus.WAITING,
                maxPlayers = 3,
                roundTimeSeconds = 180,
              }: GameArgs) {
    this.gameId = gameId;
    this.creatorId = creatorId;
    this.createdAt = new Date(createdAt);
    this.startedAt = startedAt ? new Date(startedAt) : null;
    this.endedAt = endedAt ? new Date(endedAt) : null;
    this.status = status;
    this.maxPlayers = maxPlayers;
    this.roundTimeSeconds = roundTimeSeconds;
  }

}


export default Game;
