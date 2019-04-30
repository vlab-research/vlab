import React from 'react';

import { QueryRenderer } from '@cubejs-client/react';

import { Cube } from '../../services';
import './ResponseScreen.css';

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
        cubejsApi={Cube}
        render={renderHistogram(histogram)}
      />
    </div>
  );
};

export default ResponseScreen;
