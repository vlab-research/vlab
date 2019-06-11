import React from 'react';
import { Router, Route } from 'react-router-dom';
import { Layout } from 'antd';
import { App, LoginScreen, SurveyScreen } from './containers';
import { Navbar, PrivateRoute, Spinner } from './components';
import { Auth, History } from './services';

const { Header, Content } = Layout;

const handleAuthentication = ({ location }) => {
  if (/access_token|id_token|error/.test(location.hash)) {
    Auth.handleAuthentication();
  }
};

const Root = () => {
  return (
    <Router history={History}>
      <Layout style={{ height: '100vh' }}>
        <Header style={{ background: '#fff' }}>
          <Navbar auth={Auth} />
        </Header>
        <Content style={{ padding: '0 50px', marginTop: 30 }}>
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
        </Content>
      </Layout>
    </Router>
  );
};

export default Root;
