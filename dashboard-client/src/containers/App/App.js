import React, { useEffect } from 'react';
import api from '../../services/api';
import Accounts from '../Accounts';

import './App.css';

const App = () => {
  // Create user if not exists after succesful login
  useEffect(() => {
    api.fetcher({ path: '/users', method: 'POST', body: {} })
      .catch(e => alert(e));
  }, []);

  return (
    <>
      <Accounts />
    </>
  );
};

export default App;
