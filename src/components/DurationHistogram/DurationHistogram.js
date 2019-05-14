import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { Select } from 'antd';
import { Spinner, Histogram } from '..';
import { Cube } from '../../services';
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

const DurationHistogram = ({ formid }) => {
  const stepIntervals = {
    '30 mins': 30,
    '1 hour': 60,
    '3 hours': 180,
  };

  const [intervalStep, setIntervalStep] = useState('1 hour');

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
    <div className="chart-container-b">
      <div className="info-container-b">
        <h3>Duration per user</h3>
        <div className="selector-container">
          <div className="selector-title">Interval</div>
          {renderSelector()}
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
          cubejsApi={Cube}
          render={renderHistogram(Histogram, stepIntervals[intervalStep])}
        />
      </div>
    </div>
  );
};

DurationHistogram.propTypes = {
  formid: PropTypes.string.isRequired,
};

export default DurationHistogram;
