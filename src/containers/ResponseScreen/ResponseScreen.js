import React from 'react';
import { ApiClient, Hook } from '../../services';

import './ResponseScreen.css';

const ResponseScreen = () => {
  const responses = Hook.useMountFetch({ path: '/responses' }, []);

  return (
    <div>
      {responses.map(response => (
        <>
          <h1>{response.userid}</h1>
          <button type="button" onClick={() => ApiClient.getCSV(response.formid)}>
            Download
          </button>
        </>
      ))}
    </div>
  );
};

export default ResponseScreen;
