import React from 'react';
import PropTypes from 'prop-types';

import './LoginScreen.css';

const LoginScreen = ({ auth }) => {
  const { isAuthenticated } = auth;
  return (
    <div>
      {!isAuthenticated() ? (
        <button type="button" onClick={auth.login}>
          Login!
        </button>
      ) : (
        <button type="button" onClick={auth.logout}>
          Logout!
        </button>
      )}
    </div>
  );
};

LoginScreen.propTypes = {
  auth: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default LoginScreen;
