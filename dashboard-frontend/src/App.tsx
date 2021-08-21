import React from 'react';
import { ReactQueryConfigProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query-devtools';
import { BrowserRouter, Switch, Route } from 'react-router-dom';
import StudiesPage from './pages/StudiesPage/StudiesPage';
import StudyPage from './pages/StudyPage/StudyPage';

const App = () => (
  <React.Fragment>
    <ReactQueryConfigProvider
      config={{
        queries: {
          retry: process.env.REACT_APP_RUNNING_IN_E2E_MODE ? false : 3,
          refetchOnWindowFocus: !process.env.REACT_APP_RUNNING_IN_E2E_MODE,
        },
      }}
    >
      <Routes />
    </ReactQueryConfigProvider>
    <ReactQueryDevtools />
  </React.Fragment>
);

const Routes = () => (
  <BrowserRouter>
    <Switch>
      <Route exact path="/">
        <StudiesPage />
      </Route>

      <Route path="/studies/:studySlug">
        <StudyPage />
      </Route>
    </Switch>
  </BrowserRouter>
);

export default App;
