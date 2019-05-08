import React from 'react';
import PropTypes from 'prop-types';
import { QueryRenderer } from '@cubejs-client/react';

import { Spinner, Histogram } from '..';
import { Cube } from '../../services';
import { computeData } from './chartUtil';
import './DurationHistogram.css';

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
    <div className="report-container">
      <div className="info-container">
        <h3>Duration per user</h3>
      </div>
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
  );
};

DurationHistogram.propTypes = {
  formid: PropTypes.string.isRequired,
};

export default DurationHistogram;
