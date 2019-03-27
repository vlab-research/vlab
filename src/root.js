import React from 'react';
import { Route, Router } from 'react-router-dom';
import App from './containers/App';
import Spinner from './components/Spinner';
import Auth from './services/auth';
import history from './services/history';

const auth = new Auth();

const handleAuthentication = ({ location }) => {
  if (/access_token|id_token|error/.test(location.hash)) {
    auth.handleAuthentication();
  }
};

const Root = () => {
  return (
    <Router history={history}>
      <div>
        <Route path="/" render={props => <App auth={auth} {...props} />} />
        <Route
          path="/auth"
          render={props => {
            handleAuthentication(props);
            return <Spinner {...props} />;
          }}
        />
      </div>
    </Router>
  );
};

export default Root;
