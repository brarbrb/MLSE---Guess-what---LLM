import React from 'react';
import './RoomBoardSection.scss';


interface BoardProps {
}

interface LeaderProps {
}

interface GuesserProps {
}

const RoomBoardSection: React.FC<BoardProps> = () => {
  return (
    <section className="board">
      {/* TODO header */}
      <h2>Guess or describe the word!</h2>
    </section>
  );
};

const RoomBoardLeader: React.FC<LeaderProps> = () => {
  return (
    <div className="board-leader">
      <h3>Your word is: Apple</h3>
      <b>Forbidden words:</b>
      <ul id="forbidden-words">
        <li>Apple</li>
        <li>fruit</li>
        <li>red</li>
        <li>green</li>
        <li>tree</li>
        <li>iphone</li>
        <li>mac</li>
        <li>ipad</li>
        <li>earpods</li>
        <li>newton</li>
      </ul>
      <form id="describer-form">
        <label htmlFor="description-input">Enter Description: <input id="description-input" type="text"/></label>
        <input type="submit" value="Send Description"/>
      </form>
    </div>
  );
};

const RoomBoarGuesser: React.FC<GuesserProps> = () => {
  return (
    <div className="board-guesser">
      <h3>Try to guess the word</h3>
      <div>
        <b>Description:</b> <span id="current-description"></span>
      </div>
      <form id="guesser-form">
        <label htmlFor="guess-input">Enter Your Guess: <input id="guess-input" type="text"/></label>
        <input type="submit" value="Guess"/>
      </form>
    </div>
  );
};

export default RoomBoardSection;
