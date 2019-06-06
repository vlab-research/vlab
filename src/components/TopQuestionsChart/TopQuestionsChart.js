import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { Select } from 'antd';
import { HorizontalChart, Spinner } from '..';
import { computeChartData } from './chartUtil';
import './TopQuestionsChart.css';

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
  const initialInterval = stepIntervals[1] ? stepIntervals[1] : stepIntervals[0];

  const [intervalStep, setIntervalStep] = useState(initialInterval);

  const renderSelector = () => {
    return (
      <Select
        defaultValue={intervalStep}
        onSelect={value => setIntervalStep(value)}
        dropdownRender={menu => <div>{menu}</div>}
      >
        {stepIntervals.map(interval => (
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
        <h3>{`Top ${intervalStep} Questions`}</h3>
        <div className="selector-container">
          <div className="selector-title">nº questions</div>
          {renderSelector()}
        </div>
      </div>
      <div className="histogram-container">
        <HorizontalChart
          xAxisKey="question"
          barKey="answers"
          resultSet={computeChartData(resultSet, intervalStep)}
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
