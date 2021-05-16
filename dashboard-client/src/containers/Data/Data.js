import React from 'react';
import PropTypes from 'prop-types';
import { Row, Col } from 'antd';
import { useLocation } from 'react-router-dom';
import { Cube, Auth } from '../../services';
import { StartTimeReport, DurationReport } from '..';
import AnswersReport from '../AnswersReport';
import JoinTimeReport from '../JoinTimeReport';


const DataScreen = ({ surveys }) => {
  const location = useLocation();
  const query = new URLSearchParams(location.search);
  const shortcode = query.get('shortcode');
  const surveyid = query.get('surveyid');

  let formids;

  if (surveyid) {
    formids = surveys.filter(s => s.id === surveyid).map(s => s.id);
  } else if (shortcode) {
    formids = surveys.filter(s => s.shortcode === shortcode).map(s => s.id);
  } else {
    return null;
  }

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
    </div>
  );
};

DataScreen.propTypes = {
  surveys: PropTypes.arrayOf(PropTypes.object),
};


export default DataScreen;
