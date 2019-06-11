import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { HorizontalChart, Spinner, IntervalSelector } from '../../components';
import { computeChartData } from './chartUtil';
import './TopQuestionsReport.css';

const ChartBox = ({ resultSet }) => {
  const getIntervals = () => {
    let max = resultSet.rawData().length;
    max = 10;
    if (max >= 10) max = 10;
    const lower = Math.floor(max / 3);
    const middle = Math.floor(max / 2);
    if (max <= 1) return [max];
    if (lower === middle || lower <= 1) return [middle, max];
    return [lower, middle, max];
  };
  const stepIntervals = getIntervals();

  const [activeInterval, setActiveInterval] = useState(
    stepIntervals[1] ? stepIntervals[1] : stepIntervals[0],
  );

  return (
    <div className="chart-container">
      <div className="info-container">
        <h3>{`Top ${activeInterval} Questions`}</h3>
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
          barKey="answers"
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
          dimensions: ['Responses.questionId'],
          timeDimensions: [
            {
              dimension: 'Responses.timestamp',
            },
          ],
          filters: [
            {
              dimension: 'Responses.formid',
              operator: 'equals',
              values: [formid],
            },
          ],
          measures: ['Responses.count'],
        }}
        cubejsApi={cubejs}
        render={renderChart(ChartBox, null)}
      />
    </>
  );
};

ChartBox.propTypes = {
  resultSet: PropTypes.arrayOf(PropTypes.object).isRequired,
};

TopQuestionsChart.propTypes = {
  formid: PropTypes.string.isRequired,
  cubejs: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default TopQuestionsChart;
