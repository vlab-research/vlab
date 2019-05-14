import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { Button, Menu } from 'antd';

const Navbar = ({ auth }) => {
  const isAuth = auth.isAuthenticated();

  const [page, setPage] = useState('home');

  return (
    <Menu
      onClick={e => setPage(e.key)}
      selectedKeys={[page]}
      mode="horizontal"
      style={{ lineHeight: '64px' }}
    >
      <Menu.Item key="home">
        <Link to="/">Home</Link>
      </Menu.Item>
      <Menu.Item key="surveys">
        <Link to="/surveys/form1">Surveys</Link>
      </Menu.Item>
      <Menu.Item key="logout" style={{ float: 'right' }}>
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
