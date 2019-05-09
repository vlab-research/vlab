import React from 'react';
import PropTypes from 'prop-types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

import './Histogram.css';

const Histogram = ({ resultSet, xAxisKey, barKey }) => {
  return resultSet.length ? (
    <ResponsiveContainer>
      <BarChart
        data={resultSet}
        margin={{
          left: -10,
        }}
      >
        <XAxis
          dataKey={xAxisKey}
          label={{ value: 'Minutes', position: 'insideBottomRight', offset: 0 }}
        />
        <YAxis label={{ value: barKey, angle: -90, position: 'insideLeft' }} />
        <Tooltip />
        <Bar dataKey={barKey} fill="#82ca9d" />
      </BarChart>
    </ResponsiveContainer>
  ) : (
    <h1>No data available for this form!</h1>
  );
};

Histogram.propTypes = {
  barKey: PropTypes.string.isRequired,
  xAxisKey: PropTypes.string.isRequired,
  resultSet: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default Histogram;
