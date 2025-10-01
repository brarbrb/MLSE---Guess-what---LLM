import React from 'react';

import User from "@/types/User";
import GamePlayer from "@/types/GamePlayer";

import './RoomBoardSection.scss';

interface Props {
  winners: User[];
  maxScore: number;
}

const RoomResultsSection: React.FC<Props> = ({winners, maxScore}) => {
  if (!maxScore) {
    return (
      <section className="board-results">
        <p>The game was canceled.</p>
      </section>
    );
  }

  return (
    <section className="board-results">
      {/* TODO header */}
      <h2>{winners.length < 2 ? "Winner:" : "Winners:"}</h2>
      <p>{winners.map((winner, i) => (
        i ? `, ${winner.username}` : winner.username
      ))} with score: {maxScore}</p>
    </section>
  );
};

export default RoomResultsSection;
