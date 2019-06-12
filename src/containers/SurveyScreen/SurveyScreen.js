import React from 'react';
import PropTypes from 'prop-types';
import { Row, Col } from 'antd';

import './SurveyScreen.css';
import { Cube, Auth } from '../../services';
import { StartTimeHistogram, DurationHistogram } from '../../components';

const SurveyScreen = ({ match }) => {
  const cubeInstance = Cube(Auth.getIdToken());
  return (
    <Row>
      <Col span={12}>
        <StartTimeHistogram cubejs={cubeInstance} formid={match.params.formid} />
      </Col>
      <Col span={12}>
        <DurationHistogram cubejs={cubeInstance} formid={match.params.formid} />
      </Col>
    </Row>
  );
};

SurveyScreen.propTypes = {
  match: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default SurveyScreen;
