import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { Spinner, Histogram, IntervalSelector } from '..';
import { computeHistogramData } from './chartUtil';
import './DurationHistogram.css';

const renderHistogram = (Component, interval) => ({ resultSet, error }) => {
  if (error) console.error(error); // eslint-disable-line no-console
  return (
    (resultSet && (
      <Component
        resultSet={computeHistogramData(resultSet, interval)}
        barKey="Users"
        xAxisKey="interval"
      />
    )) || <Spinner />
  );
};

const DurationHistogram = ({ formid, cubejs }) => {
  const stepIntervals = {
    '30 mins': 30,
    '1 hour': 60,
    '3 hours': 180,
  };

  const [activeInterval, setActiveInterval] = useState('1 hour');

  return (
    <div className="chart-container-b">
      <div className="info-container-b">
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
            dimensions: ['Responses.userid', 'Responses.formid'],
            filters: [
              {
                dimension: 'Responses.formid',
                operator: 'equals',
                values: [formid],
              },
            ],
          }}
          cubejsApi={cubejs}
          render={renderHistogram(Histogram, stepIntervals[activeInterval])}
        />
      </div>
    </div>
  );
};

DurationHistogram.propTypes = {
  formid: PropTypes.string.isRequired,
  cubejs: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default DurationHistogram;
