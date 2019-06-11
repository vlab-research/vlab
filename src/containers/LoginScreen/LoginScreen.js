import React from 'react';
import PropTypes from 'prop-types';
import { Button, Card } from 'antd';

import './LoginScreen.css';

const LoginScreen = ({ auth }) => {
  const isAuthenticated = auth.isAuthenticated();
  return (
    <div className="login-container">
      <Card className="card-container">
        <p style={{ 'fontSize': '120px' }}>VL</p>
        <Button onClick={isAuthenticated ? auth.logout : auth.login} type="normal" size="large">
          {isAuthenticated ? 'Logout' : 'Login'}
        </Button>
      </Card>
    </div>
  );
};

LoginScreen.propTypes = {
  auth: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default LoginScreen;
