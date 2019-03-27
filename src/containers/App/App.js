import React from 'react';
import PropTypes from 'prop-types';

import './App.css';

const App = ({ auth }) => {
  const { isAuthenticated } = auth;
  return (
    <div>
      {!isAuthenticated() ? (
        <button type="button" onClick={auth.login}>
          Login!
        </button>
      ) : (
        'LOGGED!'
      )}
    </div>
  );
};

App.propTypes = {
  auth: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default App;
