import React from 'react';
import { BrowserRouter as Router, Route } from 'react-router-dom';
import { App, LoginScreen, SurveyScreen } from './containers';
import { PrivateRoute, Spinner } from './components';
import { Auth } from './services';

const handleAuthentication = ({ location, history }) => {
  if (/access_token|id_token|error/.test(location.hash)) {
    Auth.handleAuthentication(history);
  }
};

const Root = () => {
  return (
    <div>
      <Router>
        <PrivateRoute exact path="/" component={App} auth={Auth} />
        <PrivateRoute exact path="/surveys/:formid" component={SurveyScreen} auth={Auth} />
        <Route exact path="/login" render={props => <LoginScreen {...props} auth={Auth} />} />
        <Route
          path="/auth"
          render={props => {
            handleAuthentication(props);
            return <Spinner {...props} />;
          }}
        />
      </Router>
    </div>
  );
};

export default Root;
