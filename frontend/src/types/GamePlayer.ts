interface GamePlayerArgs {
  gameId: number;
  userId: number;
  joinedAt: string;
  score?: number;
}

export class GamePlayer {
  gameId: number;
  userId: number;
  joinedAt: Date;
  score: number;

  constructor({
                gameId,
                userId,
                score = 0,
                joinedAt,
              }: GamePlayerArgs) {
    this.gameId = gameId;
    this.userId = userId;
    this.score = score || 0;
    this.joinedAt = new Date(joinedAt);
  }
}

export default GamePlayer;
