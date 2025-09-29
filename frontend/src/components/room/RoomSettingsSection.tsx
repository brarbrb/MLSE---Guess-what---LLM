import React, {useState} from 'react';
import Game from "@/types/Game";

// import './RoomSettingsSection.scss';

interface Props {
  game: Game;
}

function updateNumber(prev: { [k: string]: any }, key: string, value: string, min: number, max: number) {
  const valueNumber = Number(value || "NaN");
  console.log(`${key}: ${value} -> ${valueNumber}`)
  if (isNaN(valueNumber)) {
    return prev;
  }
  return {...prev, [key]: Math.max(min, Math.min(valueNumber, max))};
}

const RoomSettingsSection: React.FC<Props> = ({game}) => {
  // Get room id from URL/router

  // use a webhook (make sure to close the webhook on unmount)

  const [updates, setUpdates] = useState<Partial<Game>>({});

  return (
    <section className="settings">
      {/* TODO: Apply the changes to the game settings */}
      <form>
        <label htmlFor="max-players">
          Max players
          <input id="max-players" type="number" step="1" min="3" max="10"
                 value={updates.maxPlayers ?? game.maxPlayers}
                 onChange={(e) => setUpdates(prev => (
                   updateNumber(prev, "maxPlayers", e.target.value, 3, 10)
                 ))}/>
        </label>
        <label htmlFor="round-time">
          Round Time (in seconds)
          <input id="round-time" type="number" step="1" min="10" max="600"
                 value={updates.roundTimeSeconds ?? game.roundTimeSeconds}
                 onChange={(e) => setUpdates(prev => (
                   updateNumber(prev, "roundTimeSeconds", e.target.value, 10, 600)
                 ))}/>
        </label>
        <button type="submit">Apply</button>
      </form>
    </section>
  );
};

export default RoomSettingsSection;
