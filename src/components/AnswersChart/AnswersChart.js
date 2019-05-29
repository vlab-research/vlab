import React from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { AnsChart, Spinner } from '..';
import './AnswersChart.css';

const mockQuest = [
  { question: 'How are you?', freq: 10 },
  { question: 'Where do you come from?', freq: 8 },
  { question: 'Are you ready?', freq: 2 },
];

const computeChartData = () => {
  return mockQuest;
};

const renderChart = Component => ({ resultSet, error }) => {
  if (error) console.error(error); // eslint-disable-line no-console
  return (
    (resultSet && (
      <Component resultSet={computeChartData(resultSet)} xAxisKey="question" barKey="freq" />
    )) || <Spinner />
  );
};

const AnswersChart = ({ formid, cubejs }) => {
  return (
    <div className="chart-container">
      <div className="info-container">
        <h3>Top Answers</h3>
      </div>
      <div className="histogram-container">
        <QueryRenderer
          query={{
            dimensions: ['Responses.userid', 'Responses.flowid'],
            filters: [
              {
                dimension: 'Responses.formid',
                operator: 'equals',
                values: [formid],
              },
            ],
          }}
          cubejsApi={cubejs}
          render={renderChart(AnsChart, null)}
        />
      </div>
    </div>
  );
};

AnswersChart.propTypes = {
  formid: PropTypes.string.isRequired,
  cubejs: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default AnswersChart;
