import cubejs from '@cubejs-client/core';

export default function(token) {
  return cubejs(`Bearer ${token}`, {
    apiUrl: `${process.env.REACT_APP_SERVER_URL}/cubejs-api/v1`,
  });
}
