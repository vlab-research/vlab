export default {
  clientID: process.env.REACT_APP_TYPEFORM_CLIENT_ID,
  typeformUrl: process.env.REACT_APP_TYPEFORM_AUTH_URL,
  redirect_uri: process.env.REACT_APP_TYPEFORM_REDIRECT_URL,
  scope: ['accounts:read', 'forms:read'],
};
