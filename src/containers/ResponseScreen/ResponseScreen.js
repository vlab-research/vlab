import React from 'react';
import { useMountFetch } from '../../services/hooks';
import ApiClient from '../../services/api';

import './ResponseScreen.css';

const ResponseScreen = () => {
  const responses = useMountFetch({ path: '/responses' }, []);

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
