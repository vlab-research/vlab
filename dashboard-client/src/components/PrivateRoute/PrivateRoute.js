import React from 'react';
import PropTypes from 'prop-types';
import { Route, Redirect } from 'react-router-dom';
import { Navbar } from '..';
import { Layout, Spin } from 'antd';

const { Header, Content } = Layout;

const PrivateRoute = ({ component: Component, auth, ...rest }) => (
  <Route
    {...rest}
    render={props => (auth.isAuthenticated() ? (
      <>
        <Header style={{ background: '#fff' }}>
          <Navbar auth={auth} />
        </Header>
        <Content>
          <Component {...props} />
        </Content>
      </>
    ) : (auth.renewing ? (<Spin size="large" style={{ margin: '45vh auto' }} />) : (
      <Redirect
        to={{
          pathname: '/login',
        }}
      />
    )))
    }
  />
);

PrivateRoute.propTypes = {
  component: PropTypes.func.isRequired,
  auth: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default PrivateRoute;
