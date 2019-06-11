import React from 'react';
import PropTypes from 'prop-types';
import { Row, Col } from 'antd';

import './SurveyScreen.css';
import { Cube, Auth } from '../../services';
import { StartTimeReport, DurationReport, TopQuestionsReport } from '..';

const SurveyScreen = ({ match }) => {
  const cubeInstance = Cube(Auth.getIdToken());
  return (
    <div>
      <Row>
        <Col span={12}>
          <StartTimeReport cubejs={cubeInstance} formid={match.params.formid} />
        </Col>
        <Col span={12}>
          <DurationReport cubejs={cubeInstance} formid={match.params.formid} />
        </Col>
      </Row>
      <Row>
        <Col span={12}>
          <TopQuestionsReport cubejs={cubeInstance} formid={match.params.formid} />
        </Col>
      </Row>
    </div>
  );
};

SurveyScreen.propTypes = {
  match: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default SurveyScreen;
