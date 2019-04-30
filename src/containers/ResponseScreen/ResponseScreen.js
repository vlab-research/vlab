import React from 'react';

import cubejs from '@cubejs-client/core';
import { QueryRenderer } from '@cubejs-client/react';

import './ResponseScreen.css';

const cubejsApi = cubejs(process.env.REACT_APP_CUBEJS_API_TOKEN, {
  apiUrl: `${process.env.REACT_APP_SERVER_URL}/cubejs-api/v1`,
});

const histogram = ({ resultSet }) => <div>Histogram</div>;

const renderHistogram = Component => ({ resultSet, error }) => {
  return (resultSet && <Component resultSet={resultSet} />) || <div>Loading...</div>;
};

const ResponseScreen = () => {
  return (
    <div>
      <QueryRenderer
        query={{
          dimensions: [],
          timeDimensions: [
            {
              dimension: 'Responses.timestamp',
              granularity: 'day',
            },
          ],
          measures: ['Responses.uniqueUserCount'],
          filters: [],
        }}
        cubejsApi={cubejsApi}
        render={renderHistogram(histogram)}
      />
    </div>
  );
};

export default ResponseScreen;
