import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { Spinner, Histogram, IntervalSelector } from '../../components';
import { computeHistogramData } from './chartUtil';
import './AnswersReport.css';

const renderHistogram = (Component, interval) => ({ resultSet, error }) => {

  if (error) console.error(error); // eslint-disable-line no-console
  return (
    (resultSet && (
      <Component
        resultSet={computeHistogramData(resultSet, interval, 'Responses.count')}
        barKey="Users"
        xAxisKey="interval"
      />
    )) || <Spinner />
  );
};

const AnswersReport = ({ formids, cubejs }) => {
  const stepIntervals = {
    '2': 2,
    '4': 4,
    '8': 8,
  };

  const [activeInterval, setActiveInterval] = useState('4');

  return (
    <div className="chart-container">
      <div className="info-container">
        <h3>Answers</h3>
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
            measures: ['Responses.count'],
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

AnswersReport.propTypes = {
  formids: PropTypes.arrayOf(PropTypes.string).isRequired,
  cubejs: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default AnswersReport;
