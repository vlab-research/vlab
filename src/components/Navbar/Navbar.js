import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { Button, Menu } from 'antd';

const Navbar = ({ auth }) => {
  const isAuth = auth.isAuthenticated();

  return (
    <Menu mode="horizontal" selectedKeys={[]} style={{ lineHeight: '64px' }}>
      <Menu.Item>
        <Link to="/">Home</Link>
      </Menu.Item>
      <Menu.Item>
        <Link to="/surveys/form1">Surveys</Link>
      </Menu.Item>
      <Menu.Item style={{ float: 'right' }}>
        <Button onClick={isAuth ? auth.logout : auth.login} type="normal" size="large">
          {isAuth ? 'Logout' : 'Login'}
        </Button>
      </Menu.Item>
    </Menu>
  );
};

Navbar.propTypes = {
  auth: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default Navbar;
