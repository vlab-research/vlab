import React from 'react';

import { Router, Route } from 'react-router-dom';
import { Layout } from 'antd';
import {
  App, LoginScreen, Surveys,
} from './containers';
import { PrivateRoute, Spinner } from './components';
import { TypeformCreateAuth } from './components/TypeformCreate/TypeformCreate';
import { Auth, History } from './services';

const handleAuthentication = ({ location }) => {
  if (/access_token|id_token|error/.test(location.hash)) {
    Auth.handleAuthentication();
  }
};

const Root = () => (
  <Layout style={{ height: '100vh' }}>
    <Router history={History}>
      <PrivateRoute exact path="/" component={App} auth={Auth} />
      <PrivateRoute exact path="/surveys/auth" component={TypeformCreateAuth} auth={Auth} />
      <PrivateRoute path="/surveys/:survey?" component={Surveys} auth={Auth} />
      <Route exact path="/login" render={props => <LoginScreen {...props} auth={Auth} />} />
      <Route
        path="/auth"
        render={(props) => {
          handleAuthentication(props);
          return <Spinner {...props} />;
        }}
      />
    </Router>
  </Layout>
);

export default Root;
