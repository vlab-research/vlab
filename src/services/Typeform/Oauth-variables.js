export default {
  clientID: process.env.REACT_APP_TYEPFORM_CLIENT_ID,
  clientSecret: process.env.REACT_APP_TYEPFORM_CLIENT_SECRET,
  redirect_uri: 'http://localhost:3000/surveys/auth',
  scope: ['accounts:read', 'forms:read'],
};
