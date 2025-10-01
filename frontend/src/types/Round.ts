interface RoundArgs {
  gameId: number;
  roundId: number;
  leaderId: number;
  targetWord: string;
  startTime: string;
  endTime?: string | null;
}

export class Round {
  gameId: number;
  roundId: number;
  leaderId: number;
  targetWord: string;
  startTime: Date;
  endTime: Date | null;

  constructor({
                gameId,
                roundId,
                leaderId,
                targetWord,
                startTime,
                endTime,
              }: RoundArgs) {
    this.gameId = gameId;
    this.roundId = roundId;
    this.leaderId = leaderId;
    this.targetWord = targetWord;
    this.startTime = new Date(startTime);
    this.endTime = endTime ? new Date(endTime) : null;
  }
}

export default Round;
