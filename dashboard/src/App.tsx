import React, { useEffect } from 'react';
import { Auth0Provider, useAuth0 } from '@auth0/auth0-react';

import { QueryClient, QueryClientProvider, useQuery } from 'react-query'
import { BrowserRouter, Switch, Route, Redirect } from 'react-router-dom';
import StudiesPage from './pages/StudiesPage/StudiesPage';
import StudyPage from './pages/StudyPage/StudyPage';
import LoginPage from './pages/LoginPage/LoginPage';
import NewStudyPage from './pages/NewStudyPage/NewStudyPage';
import AccountsPage from './pages/AccountsPage/AccountsPage';
import StudyConfPage from './pages/StudyConfPage/StudyConfPage';
import useAuthenticatedApi from './hooks/useAuthenticatedApi';
import LoadingPage from './components/LoadingPage';

import 'notyf/notyf.min.css';

const areTestsRunning =
  process.env.REACT_APP_RUNNING_IN_E2E_MODE || process.env.NODE_ENV === 'test';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: areTestsRunning ? false : 3,
      refetchOnWindowFocus: !areTestsRunning,
    },
  }
})

const App = () => (
  <React.Fragment>
    <QueryClientProvider client={queryClient}>
      <Auth0Provider
        domain={process.env.REACT_APP_AUTH0_DOMAIN!}
        clientId={process.env.REACT_APP_AUTH0_CLIENT_ID!}
        redirectUri={window.location.origin}
        audience={process.env.REACT_APP_AUTH0_AUDIENCE!}
        cacheLocation="localstorage"
      >
        <Routes />
      </Auth0Provider>
    </QueryClientProvider>
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
        <AuthenticatedRoute exact path="/studies">
          <StudiesPage />
        </AuthenticatedRoute>

        <AuthenticatedRoute path="/studies/:studySlug/:conf">
          <StudyConfPage />
        </AuthenticatedRoute>

        <AuthenticatedRoute path="/studies/:studySlug">
          <StudyPage />
        </AuthenticatedRoute>

        <AuthenticatedRoute path="/new-study">
          <NewStudyPage />
        </AuthenticatedRoute>

        <AuthenticatedRoute path="/accounts">
          <AccountsPage />
        </AuthenticatedRoute>

        <Route
          path="/login"
          render={() =>
            isAuthenticated ? <Redirect to="/studies" /> : <LoginPage />
          }
        />

        <AuthenticatedRoute exact path="/">
          <StudiesPage />
        </AuthenticatedRoute>
      </Switch>
    </BrowserRouter>
  );
};

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

  useEffect(() => {
    if (query.data?.data) {
      query.data.data.orgs.forEach(org => {
        // Defaults to the user personal org
        if (org.name === query.data?.data.id) {
          sessionStorage.setItem('current-vlab-org', org.id);
        }
      });
    }
  }, [query.data]);

  const inProgress = !query.isSuccess && !query.isError;

  return {
    inProgress,
    failed: query.isError,
  };
};

export default App;
