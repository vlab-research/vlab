import React from 'react';
import PropTypes from 'prop-types';
import { Route, Redirect } from 'react-router-dom';

import Navbar from '../Navbar';

const PrivateRoute = ({ component: Component, auth, ...rest }) => (
  <Route
    {...rest}
    render={props =>
      auth.isAuthenticated() ? (
        <>
          <Navbar auth={auth} {...props} />
          <Component {...props} />
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
