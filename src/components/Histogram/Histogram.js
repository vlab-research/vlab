import React from 'react';
import PropTypes from 'prop-types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

import './Histogram.css';

const Histogram = ({ resultSet, xAxisKey, barKey }) => {
  return resultSet.length ? (
    <ResponsiveContainer>
      <BarChart data={resultSet}>
        <XAxis dataKey={xAxisKey} />
        <YAxis />
        <Tooltip />
        <Legend />
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
