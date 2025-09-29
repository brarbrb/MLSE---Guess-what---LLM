import React from 'react';
import logo from "@/static/images/logo.png";

import "./AppHeader.scss"

interface Props {
}

const AppHeader: React.FC<Props> = () => {
  return (
    <header style={{display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5em"}}>
      <img src={logo} alt="Logo"/>
      <nav>
        <span id="username"></span>
        <button id="login-button">Login</button>
      </nav>
    </header>
  );
};

export default AppHeader;
