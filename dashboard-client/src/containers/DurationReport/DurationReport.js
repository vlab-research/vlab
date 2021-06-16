import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { Spinner, Histogram, IntervalSelector } from '../../components';
import { computeHistogramData } from './chartUtil';
import './DurationReport.css';

const renderHistogram = (Component, interval, intervalFn) => ({ resultSet, error }) => {
  if (error) console.error(error); // eslint-disable-line no-console
  return (
    (resultSet && (
      <Component
        resultSet={computeHistogramData(resultSet, interval, intervalFn)}
        barKey="Users"
        xAxisKey="interval"
      />
    )) || <Spinner />
  );
};

const DurationHistogram = ({ formids, cubejs }) => {
  const stepIntervals = {
    '5 min': [5, 'asMinutes'],
    '1 hour': [1, 'asHours'],
    '1 day': [1, 'asDays'],
  };

  const [activeInterval, setActiveInterval] = useState('1 hour');
  const [interval, intervalFn] = stepIntervals[activeInterval];

  return (
    <div className="chart-container">
      <div className="info-container">
        <h3>Duration per user</h3>
        <div className="selector-container">
          <div className="selector-title">Interval</div>

          <IntervalSelector
            stepIntervals={stepIntervals}
            activeInterval={activeInterval}
            handleChange={setActiveInterval}
          />
        </div>
      </div>
      <div className="histogram-container">
        <QueryRenderer
          query={{
            measures: ['Responses.startTime', 'Responses.endTime'],
            dimensions: ['Responses.userid'],
            filters: [
              {
                dimension: 'Responses.formid',
                operator: 'equals',
                values: formids,
              },
            ],
          }}
          cubejsApi={cubejs}
          render={renderHistogram(Histogram, interval, intervalFn)}
        />
      </div>
    </div>
  );
};

DurationHistogram.propTypes = {
  formids: PropTypes.arrayOf(PropTypes.string).isRequired,
  cubejs: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default DurationHistogram;
