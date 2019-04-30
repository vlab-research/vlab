import cubejs from '@cubejs-client/core';

import auth from '../auth';

export default cubejs(`Bearer ${auth.getIdToken()}`, {
  apiUrl: `${process.env.REACT_APP_SERVER_URL}/cubejs-api/v1`,
});
