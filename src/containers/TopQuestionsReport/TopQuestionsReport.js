import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { HorizontalChart, Spinner, IntervalSelector } from '../../components';
import { computeChartData, getIntervals } from './chartUtil';
import './TopQuestionsReport.css';

const ChartBox = ({ resultSet }) => {
  const intervals = getIntervals(resultSet);
  const stepIntervals = {};
  intervals.forEach(interval => {
    stepIntervals[interval] = interval;
  });

  const [activeInterval, setActiveInterval] = useState(
    intervals[1].toString() || intervals[0].toString(),
  );

  return (
    <div className="chart-container">
      <div className="info-container">
        <h3>{`Top ${activeInterval} Final Questions`}</h3>
        <div className="selector-container">
          <div className="selector-title">nº questions</div>
          <IntervalSelector
            stepIntervals={stepIntervals}
            activeInterval={activeInterval}
            handleChange={setActiveInterval}
          />
        </div>
      </div>
      <div className="histogram-container">
        <HorizontalChart
          xAxisKey="question"
          barKey="count"
          resultSet={computeChartData(resultSet, activeInterval)}
        />
      </div>
    </div>
  );
};

const renderChart = Component => ({ resultSet, error }) => {
  if (error) console.error(error); // eslint-disable-line no-console

  return (resultSet && <Component resultSet={resultSet} />) || <Spinner />;
};

const TopQuestionsChart = ({ formid, cubejs }) => {
  return (
    <>
      <QueryRenderer
        query={{
          dimensions: ['LastQuestions.questionText', 'LastQuestions.questionRef'],
          filters: [
            {
              dimension: 'LastQuestions.formid',
              operator: 'equals',
              values: [formid],
            },
          ],
          measures: ['LastQuestions.count'],
        }}
        cubejsApi={cubejs}
        render={renderChart(ChartBox, null)}
      />
    </>
  );
};

ChartBox.propTypes = {
  resultSet: PropTypes.objectOf(PropTypes.object).isRequired,
};

TopQuestionsChart.propTypes = {
  formid: PropTypes.string.isRequired,
  cubejs: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default TopQuestionsChart;
