import React from 'react';

import { ResponsiveContainer, BarChart, XAxis, YAxis, Bar } from 'recharts';
import moment from 'moment';

import { QueryRenderer } from '@cubejs-client/react';
import cubejs from '../../services/cube';
import { StartTimeHistogram } from '../../components';

import './ResponseScreen.css';

const cubejsApi = cubejs;

const histogram = ({ resultSet }) => {
  const data = resultSet
    .rawData()
    .filter(response => response['Responses.formid'] === 'form1')
    .map(response => {
      const start = moment(response['Responses.startTime']);
      const end = moment(response['Responses.endTime']);
      return {
        duration: moment.duration(end.diff(start)).asMinutes(),
        userid: response['Responses.userid'],
      };
    });
  const range = 60;
  const freqData = {};
  data.forEach(el => {
    let max = Math.ceil(el.duration / range) * range;
    if (!max) max = range;
    freqData[max] = freqData[max] ? freqData[max] + 1 : 1;
  });

  const maxDuration = Math.max(...Object.keys(freqData));
  const chartData = [];
  for (let i = 0; i < maxDuration; i += range) {
    let freq = freqData[i + range];
    if (!freq) freq = 0;
    chartData.push({ interval: `${i} - ${i + range}`, freq });
  }

  return (
    <ResponsiveContainer width={700} height="80%">
      <BarChart width={730} height={250} data={chartData}>
        <XAxis dataKey="interval" />
        <YAxis />
        <Bar dataKey="freq" fill="#82ca9d" />
      </BarChart>
    </ResponsiveContainer>
  );
};

const renderHistogram = Component => ({ resultSet, error }) => {
  return (resultSet && <Component resultSet={resultSet} />) || <div>Loading...</div>;
};

const ResponseScreen = () => {
  return (
    <div style={{ height: '100vh', width: '100vw' }}>
      <QueryRenderer
        query={{
          measures: ['Responses.startTime', 'Responses.endTime'],
          timeDimensions: [],
          dimensions: ['Responses.userid', 'Responses.formid'],
          filters: [],
        }}
        cubejsApi={cubejsApi}
        render={renderHistogram(histogram)}
      />
      <StartTimeHistogram formid="form1" />
    </div>
  );
};

export default ResponseScreen;
