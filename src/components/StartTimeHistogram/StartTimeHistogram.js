import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { Spinner, Histogram } from '..';
import { Cube } from '../../services';
import { computeHistogramData } from './chartUtil';
import './StartTimeHistogram.css';

const renderHistogram = (Component, interval) => ({ resultSet, error }) => {
  if (error) console.error(error); // eslint-disable-line no-console
  return (
    (resultSet && (
      <Component
        resultSet={computeHistogramData(resultSet, interval)}
        barKey="Users"
        xAxisKey="time"
      />
    )) || <Spinner />
  );
};

const StartTimeHistogram = ({ formid }) => {
  const stepIntervals = {
    '30m': 30,
    '1h': 60,
    '3h': 180,
  };

  const [intervalStep, setIntervalStep] = useState('30m');

  const renderSelector = () => {
    return (
      <select onChange={e => setIntervalStep(e.target.value)}>
        {Object.keys(stepIntervals).map(interval => (
          <option key={interval} value={interval}>
            {interval}
          </option>
        ))}
      </select>
    );
  };

  return (
    <div className="report-container">
      <div className="info-container">
        <h3>Users count chat start time</h3>
        {renderSelector()}
      </div>
      <QueryRenderer
        query={{
          measures: ['Responses.startTime'],
          timeDimensions: [
            {
              dimension: 'Responses.timestamp',
            },
          ],
          dimensions: ['Responses.userid'],
          filters: [
            {
              dimension: 'Responses.formid',
              operator: 'equals',
              values: [formid],
            },
          ],
        }}
        cubejsApi={Cube}
        render={renderHistogram(Histogram, stepIntervals[intervalStep])}
      />
    </div>
  );
};

StartTimeHistogram.propTypes = {
  formid: PropTypes.string.isRequired,
};

export default StartTimeHistogram;
