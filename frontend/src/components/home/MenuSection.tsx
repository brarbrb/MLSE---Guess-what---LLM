import React from 'react';
import {Link} from "react-router";
import './MenuSection.scss';

interface Props {
}

const MenuSection: React.FC<Props> = () => {
  return (
    <section className="menu">
      <h2>Game Menu</h2>
      <div className="menu-buttons">
        <Link to="/rooms">
          <button>
            Create New Game
          </button>
        </Link>
        <Link to="/rooms/1">
          <button>
            Join Existing Game
          </button>
        </Link>
        {/*<Link to="/settings">*/}
        <button>
          Settings
        </button>
        {/*</Link>*/}
      </div>
    </section>
  );
};

export default MenuSection;
