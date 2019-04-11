import React from 'react';
import { BrowserRouter as Router, Route } from 'react-router-dom';
import { App, LoginScreen, ResponseScreen } from './containers';
import { PrivateRoute, Spinner } from './components';
import { Auth } from './services';

export const auth = new Auth();

const handleAuthentication = ({ location, history }) => {
  if (/access_token|id_token|error/.test(location.hash)) {
    auth.handleAuthentication(history);
  }
};

const Root = () => {
  return (
    <Router>
      <PrivateRoute exact path="/" component={App} auth={auth} />
      <PrivateRoute exact path="/responses" component={ResponseScreen} auth={auth} />
      <Route exact path="/login" render={props => <LoginScreen {...props} auth={auth} />} />
      <Route
        path="/auth"
        render={props => {
          handleAuthentication(props);
          return <Spinner {...props} />;
        }}
      />
    </Router>
  );
};

export default Root;
