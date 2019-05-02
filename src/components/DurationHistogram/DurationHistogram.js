import React from 'react';

import { ResponsiveContainer, BarChart, XAxis, YAxis, Bar } from 'recharts';
import { QueryRenderer } from '@cubejs-client/react';
import cubejs from '../../services/cube';

import { getData } from './chartUtil';

const cubejsApi = cubejs;

const histogram = ({ data }) => {
  return (
    <ResponsiveContainer width={700} height="80%">
      <BarChart width={730} height={250} data={data}>
        <XAxis dataKey="interval" />
        <YAxis />
        <Bar dataKey="freq" fill="#82ca9d" />
      </BarChart>
    </ResponsiveContainer>
  );
};

const renderHistogram = Component => ({ resultSet, error }) => {
  return (
    (resultSet && <Component data={getData(resultSet)} />) ||
    (error && error.toString()) || <div>Loading...</div>
  );
};

const HistorgramContainer = ({ formid }) => {
  return (
    <div style={{ height: '100vh', width: '100vw' }}>
      <QueryRenderer
        query={{
          measures: ['Responses.startTime', 'Responses.endTime'],
          dimensions: ['Responses.userid', 'Responses.formid'],
          filters: [
            {
              dimension: 'Responses.formid',
              operator: 'equals',
              values: [formid],
            },
          ],
        }}
        cubejsApi={cubejsApi}
        render={renderHistogram(histogram)}
      />
    </div>
  );
};

export default HistorgramContainer;
