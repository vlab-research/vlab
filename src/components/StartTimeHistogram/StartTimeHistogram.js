import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';
import { Select } from 'antd';

import { Spinner, Histogram } from '..';
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

const StartTimeHistogram = ({ formid, cubejs }) => {
  const stepIntervals = {
    '30 mins': 30,
    '1 hour': 60,
    '3 hours': 180,
  };

  const [intervalStep, setIntervalStep] = useState('30 mins');

  const renderSelector = () => {
    return (
      <Select
        defaultValue={intervalStep}
        onSelect={value => setIntervalStep(value)}
        dropdownRender={menu => <div>{menu}</div>}
      >
        {Object.keys(stepIntervals).map(interval => (
          <Select.Option key={interval} value={interval}>
            {interval}
          </Select.Option>
        ))}
      </Select>
    );
  };

  return (
    <div className="chart-container">
      <div className="info-container">
        <h3 className="chart-title">Users count chat start time</h3>
        <div className="selector-container">
          <div className="selector-title">Interval</div>
          {renderSelector()}
        </div>
      </div>
      <div className="histogram-container">
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
          cubejsApi={cubejs}
          render={renderHistogram(Histogram, stepIntervals[intervalStep])}
        />
      </div>
    </div>
  );
};

StartTimeHistogram.propTypes = {
  formid: PropTypes.string.isRequired,
  cubejs: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default StartTimeHistogram;
