import React from 'react';
import PropTypes from 'prop-types';

import './SurveyScreen.css';
import { StartTimeHistogram, DurationHistogram } from '../../components';

const SurveyScreen = ({ match }) => {
  return (
    <div className="surveys-container">
      {/* <div className="col-6"> */}
      <StartTimeHistogram formid={match.params.formid} />
      <DurationHistogram formid={match.params.formid} />
      {/* </div> */}
    </div>
  );
};

SurveyScreen.propTypes = {
  match: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default SurveyScreen;
