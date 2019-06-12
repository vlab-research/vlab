export default {
  clientID: process.env.REACT_APP_TYEPFORM_CLIENT_ID,
  typeformUrl: process.env.REACT_APP_TYEPFORM_AUTH_URL,
  redirect_uri: process.env.REACT_APP_TYPEFORM_REDIRECT_URL,
  scope: ['accounts:read', 'forms:read'],
};
