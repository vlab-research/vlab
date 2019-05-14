import React from 'react';
import PropTypes from 'prop-types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

import './Histogram.css';

const renderTooltip = props => {
  const name = props.active ? props.payload[0].name : null;
  return (
    props.active && (
      <div className="custom_tooltip">
        <p className="custom_tooltip_label">{props.label}</p>
        <p className="custom_tooltip_name">
          {`${name} : `}
          <span className="custom_tooltip_value">{props.payload[0].payload[name]}</span>
        </p>
      </div>
    )
  );
};

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
          // label={{ value: 'Minutes', position: 'insideBottomRight', offset: 0 }}
        />
        <YAxis
          allowDecimals={false}
          domain={[0, 'dataMax']}
          // label={{ value: barKey, angle: -90, position: 'insideLeft' }}
        />
        <Tooltip content={renderTooltip} />
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
