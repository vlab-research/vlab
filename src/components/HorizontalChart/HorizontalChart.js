import React from 'react';
import PropTypes from 'prop-types';
import { ResponsiveContainer, BarChart, CartesianGrid, Bar, XAxis, YAxis, Tooltip } from 'recharts';

import './HorizontalChart.css';

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

const HorizontalChart = ({ resultSet, xAxisKey, barKey }) => {
  return resultSet.length ? (
    <ResponsiveContainer>
      <BarChart data={resultSet} layout="vertical">
        <CartesianGrid vertical={false} stroke="#f5f5f5" />
        <YAxis type="category" dataKey={xAxisKey} />
        <XAxis type="number" domain={[0, 'dataMax']} />
        <Tooltip content={renderTooltip} />
        <Bar dataKey={barKey} fill="#82ca9d" />
      </BarChart>
    </ResponsiveContainer>
  ) : (
    <h1>No data available for this form!</h1>
  );
};

HorizontalChart.propTypes = {
  barKey: PropTypes.string.isRequired,
  xAxisKey: PropTypes.string.isRequired,
  resultSet: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default HorizontalChart;
