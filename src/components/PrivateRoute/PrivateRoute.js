import React from 'react';
import PropTypes from 'prop-types';
import { Route, Redirect } from 'react-router-dom';
import { Layout } from 'antd';
import { Navbar } from '..';

const { Header, Content } = Layout;

const PrivateRoute = ({ component: Component, auth, ...rest }) => (
  <Route
    {...rest}
    render={props =>
      auth.isAuthenticated() ? (
        <>
          <Header style={{ background: '#fff' }}>
            <Navbar auth={auth} />
          </Header>
          <Content>
            <Component {...props} />
          </Content>
        </>
      ) : (
        <Redirect
          to={{
            pathname: '/login',
          }}
        />
      )
    }
  />
);

PrivateRoute.propTypes = {
  component: PropTypes.func.isRequired,
  auth: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default PrivateRoute;
