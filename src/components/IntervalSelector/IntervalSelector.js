import React from 'react';
import PropTypes from 'prop-types';
import { Select } from 'antd';
import './IntervalSelector.css';

const IntervalSelector = ({ stepIntervals, activeInterval, handleChange }) => {
  return (
    <Select
      defaultValue={activeInterval}
      onSelect={value => handleChange(value)}
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

IntervalSelector.propTypes = {
  stepIntervals: PropTypes.objectOf(PropTypes.number).isRequired,
  activeInterval: PropTypes.string.isRequired,
  handleChange: PropTypes.func.isRequired,
};

export default IntervalSelector;
