import React from 'react';
import PropTypes from 'prop-types';
import { Row, Col, Button } from 'antd';
import './SurveyScreen.css';
import { Cube, Auth } from '../../services';
import { StartTimeReport, DurationReport } from '..';
import AnswersReport from '../AnswersReport';
import JoinTimeReport from '../JoinTimeReport';
import getCsv from '../../services/api/getCSV';

const SurveyScreen = ({ formids }) => {
  const cubeInstance = Cube(Auth.getIdToken());
  return (
    <div>
      <Row>
        <Col span={12}>
          <StartTimeReport cubejs={cubeInstance} formids={formids} />
        </Col>
        <Col span={12}>
          <DurationReport cubejs={cubeInstance} formids={formids} />
        </Col>
      </Row>
      <Row>
        <Col span={12}>
          <AnswersReport cubejs={cubeInstance} formids={formids} />
        </Col>
        <Col span={12}>
          <JoinTimeReport cubejs={cubeInstance} formids={formids} />
        </Col>
      </Row>
      <Row style={{ marginTop: '2em', textAlign: 'center' }}>
        <Button size='large' onClick={() => getCsv(formids)}> DOWNLOAD CSV </Button>
      </Row>
    </div>
  );
};

SurveyScreen.propTypes = {
  formids: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default SurveyScreen;
