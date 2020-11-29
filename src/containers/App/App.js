import React from 'react';

import FacebookPages from '../FacebookPages';
import './App.css';


const pages = (res) => {
  console.log(res); // eslint-disable-line no-console
};

const App = () => (
  <div>
    <h1>Landing page</h1>
    <FacebookPages callback={pages} />
  </div>
);

export default App;
