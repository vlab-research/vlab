import React from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { Select } from 'antd';
import 'antd/dist/antd.css';
import { Spinner, Histogram } from '..';
import { Cube } from '../../services';
import { computeData } from './chartUtil';
import './DurationHistogram.css';
const { Option } = Select;

const renderHistogram = Component => ({ resultSet, error }) => {
  return (
    (resultSet && (
      <Component resultSet={computeData(resultSet, 60)} barKey="Users" xAxisKey="interval" />
    )) ||
    (error && error.toString()) || <Spinner />
  );
};

const DurationHistogram = ({ formid }) => {
  return (
    <div className="chart-container-b">
      <div className="info-container-b">
        <h3>Duration per user</h3>
        <div className="selector-container">
          <div className="selector-title">Interval</div>
          <Select defaultValue="60" dropdownRender={menu => <div>{menu}</div>}>
            <Option value="30">30 min</Option>
            <Option value="60">60 min</Option>
          </Select>
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
          render={renderHistogram(Histogram)}
        />
      </div>
    </div>
  );
};

DurationHistogram.propTypes = {
  formid: PropTypes.string.isRequired,
};

export default DurationHistogram;
