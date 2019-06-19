import React from 'react';
import PropTypes from 'prop-types';
import { Row, Col } from 'antd';

import './SurveyScreen.css';
import { Cube, Auth } from '../../services';
import { StartTimeReport, DurationReport } from '..';

const SurveyScreen = ({ formid }) => {
  const cubeInstance = Cube(Auth.getIdToken());
  return (
    <Row>
      <Col span={12}>
        <StartTimeReport cubejs={cubeInstance} formid={formid} />
      </Col>
      <Col span={12}>
        <DurationReport cubejs={cubeInstance} formid={formid} />
      </Col>
    </Row>
  );
};

SurveyScreen.propTypes = {
  formid: PropTypes.string.isRequired,
};

export default SurveyScreen;
