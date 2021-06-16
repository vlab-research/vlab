import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { Spinner, Histogram, IntervalSelector } from '../../components';
import { computeHistogramData } from './chartUtil';
import './DurationReport.css';

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

const DurationHistogram = ({ formids, cubejs }) => {

  // TODO: change intervals to be automatic based on max
  // then allow reasonable max - or manually chosen max. 
  // OR: allow intervals and just show the first X intervals
  // and allow big range of intervals...
  const stepIntervals = {
    '5 min': 5/60,
    '1 hour': 1,
    '1 day': 24,
  };

  const [activeInterval, setActiveInterval] = useState('3 hours');

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
          render={renderHistogram(Histogram, stepIntervals[activeInterval])}
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
