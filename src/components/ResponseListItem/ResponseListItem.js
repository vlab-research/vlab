import React from 'react';
import PropTypes from 'prop-types';

import { ApiClient } from '../../services';

import './ResponseListItem.css';

function parseDate(date) {
  return new Date(date).toUTCString().slice(0, -7);
}

const ResponseListItem = ({ response }) => {
  return (
    <tr className="response-list-item-row">
      <td>{response.userid}</td>
      <td>{response.formid}</td>
      <td>{parseDate(response.first_timestamp)}</td>
      <td>{response.first_response}</td>
      <td>{parseDate(response.first_timestamp)}</td>
      <td>{response.last_response}</td>
      <td>
        <button type="button" onClick={() => ApiClient.getCSV(response.formid)}>
          Download CSV
        </button>
      </td>
    </tr>
  );
};

ResponseListItem.propTypes = {
  response: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default ResponseListItem;
