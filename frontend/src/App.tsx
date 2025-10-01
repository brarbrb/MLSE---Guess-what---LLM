import React from 'react';
import {Outlet} from "react-router";
import AppHeader from "@/components/header/AppHeader";

import "@/styles/main.scss"

interface Props {
  title: string;
  data?: any;
}

const App: React.FC<Props> = ({title, data}) => {
  return (
    <>
      <AppHeader/>

      <main>
        <Outlet/>
      </main>

      <footer>
        <p style={{textAlign: "center", margin: 0}}>
          Created by Omer-Shay Becker, Barbara Aleksandrov, and Kfir Moshe Nissim.
        </p>
      </footer>
    </>
  );
};

export default App;
