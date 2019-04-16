import React from 'react';
import { Hook } from '../../services';

import { ResponseList } from '../../components';

import './ResponseScreen.css';

const ResponseScreen = () => {
  const responses = Hook.useMountFetch({ path: '/responses' }, []);

  return (
    <table className="response-screen-container">
      <thead>
        <tr className="response-list-item-row">
          <th>User id</th>
          <th>Form id</th>
          <th>First response date</th>
          <th>First response content</th>
          <th>Last response date</th>
          <th>Last response content</th>
          <th>Download</th>
        </tr>
      </thead>
      <tbody className="response-list-body">
        <ResponseList responses={responses} />
      </tbody>
    </table>
  );
};

export default ResponseScreen;
