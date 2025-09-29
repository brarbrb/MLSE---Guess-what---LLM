import React from 'react';
import './RoomBoardSection.scss';
import User from "@/types/User";
import GamePlayer from "@/types/GamePlayer";

interface Props {
  users: { [userId: number]: User };
  gamePlayers: GamePlayer[];
}

const RoomSummerySection: React.FC<Props> = ({users, gamePlayers}) => {
  const sortedGamePlayers = gamePlayers.sort((left, right) => {
    const scoreDiff = left.score - right.score;
    const joinTimeDiff = left.joinedAt.getTime() - right.joinedAt.getTime()
    return scoreDiff || joinTimeDiff;
  });

  return (
    <section className="board-summary">
      {/* TODO header */}
      <h2> players list:</h2>
      <ul>
        {sortedGamePlayers.map((gamePlayer) => (
            <li key={gamePlayer.userId}>
              <b>{users[gamePlayer.userId].username}</b>: {gamePlayer.score}
            </li>
          )
        )}
      </ul>
    </section>
  );
};

export default RoomSummerySection;
