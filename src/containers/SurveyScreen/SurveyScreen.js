import React from 'react';
import PropTypes from 'prop-types';
import { Row, Col } from 'antd';

import './SurveyScreen.css';
import { StartTimeHistogram, DurationHistogram } from '../../components';

const SurveyScreen = ({ match }) => {
  return (
    <Row>
      <Col span={12}>
        <StartTimeHistogram formid={match.params.formid} />
      </Col>
      <Col span={12}>
        <DurationHistogram formid={match.params.formid} />
      </Col>
    </Row>
  );
};

SurveyScreen.propTypes = {
  match: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default SurveyScreen;
