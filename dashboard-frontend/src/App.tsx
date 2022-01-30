import React from 'react';
import { Auth0Provider } from '@auth0/auth0-react';
import { ReactQueryConfigProvider, useQuery } from 'react-query';
import { ReactQueryDevtools } from 'react-query-devtools';
import { BrowserRouter, Switch, Route, Redirect } from 'react-router-dom';
import StudiesPage from './pages/StudiesPage/StudiesPage';
import StudyPage from './pages/StudyPage/StudyPage';
import LoginPage from './pages/LoginPage/LoginPage';
import { ReactComponent as Logo } from './assets/logo.svg';
import useAuth0 from './hooks/useAuth0';
import useAuthenticatedApi from './hooks/useAuthenticatedApi';

const areTestsRunning =
  process.env.REACT_APP_RUNNING_IN_E2E_MODE || process.env.NODE_ENV === 'test';

const App = () => (
  <React.Fragment>
    <ReactQueryConfigProvider
      config={{
        queries: {
          retry: areTestsRunning ? false : 3,
          refetchOnWindowFocus: !areTestsRunning,
        },
      }}
    >
      <Auth0Provider
        domain={process.env.REACT_APP_AUTH0_DOMAIN!}
        clientId={process.env.REACT_APP_AUTH0_CLIENT_ID!}
        redirectUri={window.location.origin}
        audience={process.env.REACT_APP_AUTH0_AUDIENCE!}
      >
        <Routes />
      </Auth0Provider>
    </ReactQueryConfigProvider>
    <ReactQueryDevtools />
  </React.Fragment>
);

const Routes = () => {
  const { isLoading, isAuthenticated } = useAuth0();
  const creatingUserState = useCreateUserForCurrentAccessToken();

  if (isLoading || (isAuthenticated && creatingUserState.inProgress)) {
    return <LoadingPage />;
  }

  if (creatingUserState.failed) {
    return <LoginPage withGenericError />;
  }

  return (
    <BrowserRouter>
      <Switch>
        <AuthenticatedRoute exact path="/">
          <StudiesPage />
        </AuthenticatedRoute>

        <AuthenticatedRoute path="/studies/:studySlug">
          <StudyPage />
        </AuthenticatedRoute>

        <Route
          path="/login"
          render={() => (isAuthenticated ? <Redirect to="/" /> : <LoginPage />)}
        />
      </Switch>
    </BrowserRouter>
  );
};

const LoadingPage = () => (
  <div
    className="h-screen flex justify-center bg-gray-100"
    data-testid="loading-page"
  >
    <div className="self-center">
      <Logo
        className="h-12 self-center animate-pulse"
        title="Virtual Lab logo"
      />
    </div>
  </div>
);

const AuthenticatedRoute = ({
  children,
  ...rest
}: React.ComponentProps<typeof Route>) => {
  const { isAuthenticated } = useAuth0();

  return (
    <Route
      {...rest}
      render={() => (isAuthenticated ? children : <Redirect to="/login" />)}
    />
  );
};

const useCreateUserForCurrentAccessToken = () => {
  const { isAuthenticated } = useAuth0();
  const { createUser } = useAuthenticatedApi();
  const query = useQuery('create-user-for-current-access-token', createUser, {
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    enabled: isAuthenticated,
  });

  const inProgress = !query.isSuccess && !query.isError;

  return {
    inProgress,
    failed: query.isError,
  };
};

export default App;
