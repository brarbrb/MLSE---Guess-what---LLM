import React, {useCallback, useMemo} from 'react';

import Game, {GameStatus} from "@/types/Game";
import GamePlayer from "@/types/GamePlayer";
import User from "@/types/User";
import Round from "@/types/Round";

import RoomSummarySection from "./RoomSummarySection";
import RoomBoardSection from "./RoomBoardSection";
import RoomChatSection from "./RoomChatSection";
import RoomSettingsSection from "./RoomSettingsSection";
import RoomResultsSection from "./RoomResultsSection";

import './RoomArticle.scss';
import ChatMessage from "@/types/Chat";

interface Props {
}

const RoomArticle: React.FC<Props> = () => {
  // Get room id from URL/router

  // use a webhook (make sure to close the webhook on unmount)
  const game: Game = new Game({
    gameId: 1,
    status: GameStatus.WAITING,
    maxPlayers: 3,
    createdAt: (new Date()).toISOString(),
    creatorId: 1,
    roundTimeSeconds: 180,
    startedAt: null,
  });
  const players: GamePlayer[] = [
    new GamePlayer({gameId: 1, userId: 1, score: 0, joinedAt: (new Date()).toISOString(),})
  ]
  const users: { [userId: number]: User } = {
    1: new User({userId: 1, username: "Test Testy"}),
  }

  /**
   * Get the current winners of the game based on max score.
   */
  const [winners, maxScore] = useMemo(() => {
    if (!players.length) {
      return [[], 0];
    }
    const maxScore = Math.max(...players.map((player) => player.score));
    if (!maxScore) {
      return [[], 0];
    }
    const winners = players.filter(player => player.score === maxScore).map(player => users[player.userId]);
    return [winners, maxScore];
  }, [players]);

  /**
   * Mock for the current round.
   */
  const currentRound = useMemo(() => {
    return null;
  }, [players]);

  /**
   * Mock for the Chat.
   * TODO
   */
  const chatMessages: ChatMessage[] = useMemo(() => {
    return [];
  }, [players]);

  const sendHint = useCallback(() => {
    // TODO: send the hint to the server (using a websocket?)
  }, [players]);

  const sendGuess = useCallback(() => {
    // TODO: send the guess to the server (using a websocket?)
  }, [players]);

  return (
    <article className="room">
      <RoomSummarySection users={users} gamePlayers={players}/> {/* Players list, current player, score, etc. */}
      {getMainSection(game, currentRound, sendHint, sendGuess, winners, maxScore)}
      <RoomChatSection chatMessages={chatMessages}/>
    </article>
  );
};

/**
 * Get the game content element based on the game status.
 */
function getMainSection(
  game: Game, currentRound: null | Round, sendHint: () => void, sendGuess: () => void, winners: User[], maxScore: number
) {
  switch (game.status) {
    case GameStatus.WAITING:
      return <RoomSettingsSection game={game}/>;
    case GameStatus.ACTIVE:
      return <RoomBoardSection/>;
    default:
      return <RoomResultsSection winners={winners} maxScore={maxScore}/>;
  }
}

export default RoomArticle;
