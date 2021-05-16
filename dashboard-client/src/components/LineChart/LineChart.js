import React from 'react';
import PropTypes from 'prop-types';
import {
  ResponsiveContainer,
  LineChart,
  CartesianGrid,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';

import './LineChart.css';

const renderTooltip = ({ active, label, payload }) => {
  const { name } = active && payload[0];
  return (
    active && (
      <div className="custom_tooltip">
        <p className="custom_tooltip_name">{label}</p>
        <p className="custom_tooltip_name">
          {`${name} : `}
          <span className="custom_tooltip_value">{payload[0].payload[name]}</span>
        </p>
      </div>
    )
  );
};

const LinesChart = ({ resultSet, xAxisKey, barKey }) => (resultSet.length ? (
  <ResponsiveContainer>
    <LineChart data={resultSet}>
      <CartesianGrid vertical={false} stroke="#f5f5f5" />
      <YAxis allowDecimals={false} domain={[0, 'dataMax']} />
      <XAxis dataKey={xAxisKey} />
      <Tooltip content={renderTooltip} />
      <Line type="monotone" dataKey={barKey} stroke="#82ca9d" dot={false} />
    </LineChart>
  </ResponsiveContainer>
) : (
  <h1>No data available for this form!</h1>
));

LinesChart.propTypes = {
  barKey: PropTypes.string.isRequired,
  xAxisKey: PropTypes.string.isRequired,
  resultSet: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default LinesChart;
