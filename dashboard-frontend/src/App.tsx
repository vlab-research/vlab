import React from 'react';
import { ReactQueryConfigProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query-devtools';
import StudiesPage from './pages/StudiesPage/StudiesPage';

const App = () => (
  <React.Fragment>
    <ReactQueryConfigProvider
      config={{
        queries: {
          retry: !process.env.REACT_APP_RUNNING_IN_E2E_MODE,
          refetchOnWindowFocus: !process.env.REACT_APP_RUNNING_IN_E2E_MODE,
        },
      }}
    >
      <StudiesPage />
    </ReactQueryConfigProvider>
    <ReactQueryDevtools />
  </React.Fragment>
);

export default App;
