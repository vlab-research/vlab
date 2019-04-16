import React from 'react';
import PropTypes from 'prop-types';

import { ResponseListItem } from '..';

const ResponseList = ({ responses }) => {
  return (
    <>
      {responses.map(response => (
        <ResponseListItem key={response.userid} response={response} />
      ))}
    </>
  );
};

ResponseList.propTypes = {
  responses: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default ResponseList;
