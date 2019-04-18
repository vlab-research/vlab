/* eslint-disable no-console */
import AUTH_CONFIG from './Oauth-variables';

class Typeform {
  createOrAuthorize = () => {
    if (this.isAuthenticated()) this.createSurvey();
    else this.authorize();
  };

  authorize = () => {
    window.location = `https://api.typeform.com/oauth/authorize?response_type=code&client_id=${
      AUTH_CONFIG.clientID
    }&scope=${AUTH_CONFIG.scope.join(' ')}&redirect_uri=${encodeURIComponent(
      AUTH_CONFIG.redirect_uri,
    )}`;
  };

  handleAuthorization = (code, history) => {
    fetch(serverUrl + code).then();
    history.push('/surveys/create');
    console.log('fetch server', code);
  };

  createSurvey = () => {
    fetch(`${serverUrl}/createSurvey`).then();
    console.log('create');
  };

  isAuthenticated = () => {
    console.log('auth');
    return false;
  };
}

export default new Typeform();
