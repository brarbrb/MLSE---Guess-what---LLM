import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter, Routes, Route} from "react-router";

import App from './App';
import './styles/main.scss';
import HomeArticle from "@/components/home/HomeArticle";
import RoomArticle from "@/components/room/RoomArticle";


// Auto-mount body components
document.addEventListener('DOMContentLoaded', () => {
  const propsJson = document.body.getAttribute('data-react-props');
  let props: { [key: string]: any } = {};
  try {
    props = propsJson ? JSON.parse(propsJson) : {};
  } catch (e) {
    // failed to parse props
    console.error(e, propsJson);
  }

  const reactRoot = ReactDOM.createRoot(document.body);
  reactRoot.render(
    <BrowserRouter>
      <Routes>
        <Route element={<App title={props.title} data={props}/>}>
          <Route index element={<HomeArticle title={props.title} data={props}/>}/>
          {/*<Route path="about" element={<About/>}/>*/}

          <Route path="rooms">
            {/*  <Route index element={<ConcertsHome/>}/>*/}
            <Route path=":pid" element={<RoomArticle/>}/>
            {/*  <Route path="new" element={<Trending/>}/>*/}
          </Route>

          {/*<Route path="*" element={<NotFound/>}/>*/}
        </Route>
      </Routes>
    </BrowserRouter>
  );
});
