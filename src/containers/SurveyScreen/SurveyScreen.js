import React from 'react';
import PropTypes from 'prop-types';
import { Row, Col } from 'antd';

import './SurveyScreen.css';
import { Cube, Auth } from '../../services';
import { StartTimeReport, DurationReport, TopQuestionsReport } from '..';
import AnswersReport from '../AnswersReport';
import JoinTimeReport from '../JoinTimeReport';

const SurveyScreen = ({ formid }) => {
  const cubeInstance = Cube(Auth.getIdToken());
  return (
    <div>
      <Row>
        <Col span={12}>
          <StartTimeReport cubejs={cubeInstance} formid={formid} />
        </Col>
        <Col span={12}>
          <DurationReport cubejs={cubeInstance} formid={formid} />
        </Col>
      </Row>
      <Row>
        <Col span={12}>
          <TopQuestionsReport cubejs={cubeInstance} formid={formid} />
        </Col>
        <Col span={12}>
          <AnswersReport cubejs={cubeInstance} formid={formid} />
        </Col>
      </Row>
      <Row>
        <Col span={12}>
          <JoinTimeReport cubejs={cubeInstance} formid={formid} />
        </Col>
      </Row>
    </div>
  );
};

SurveyScreen.propTypes = {
  formid: PropTypes.string.isRequired,
};

export default SurveyScreen;
