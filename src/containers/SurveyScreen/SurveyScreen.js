import React from 'react';
import PropTypes from 'prop-types';
import { Row, Col } from 'antd';

import './SurveyScreen.css';
import { Cube, Auth } from '../../services';
import { StartTimeReport, DurationReport } from '..';
import AnswersReport from '../AnswersReport';
import JoinTimeReport from '../JoinTimeReport';

import { Button } from 'antd';
import getCsv from '../../services/api/getCSV';

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
          <AnswersReport cubejs={cubeInstance} formid={formid} />
        </Col>
        <Col span={12}>
          <JoinTimeReport cubejs={cubeInstance} formid={formid} />
        </Col>
      </Row>
      <Row style={{ marginTop: '2em', textAlign: 'center' }}>

        <Button size='large' onClick={ () => getCsv(formid) }> DOWNLOAD CSV </Button>

      </Row>
    </div>
  );
};

SurveyScreen.propTypes = {
  formid: PropTypes.string.isRequired,
};

export default SurveyScreen;
