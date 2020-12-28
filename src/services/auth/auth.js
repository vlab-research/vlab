/* eslint-disable no-console */
import auth0 from 'auth0-js';
import history from '../history';

import AUTH_CONFIG from './auth0-variables';

class Auth {
  constructor() {
    this.auth0 = new auth0.WebAuth({
      domain: AUTH_CONFIG.domain,
      clientID: AUTH_CONFIG.clientId,
      redirectUri: AUTH_CONFIG.callbackUrl,
      responseType: 'token id_token',
      scope: 'openid email',
    });

    const loggedIn = localStorage.getItem('isLoggedIn');
    if (loggedIn) {
      this.renewSession();
    }
  }

  login = () => {
    this.auth0.authorize();
  };

  handleAuthentication = () => {
    this.auth0.parseHash((err, authResult) => {
      if (authResult && authResult.accessToken && authResult.idToken) {
        this.setSession(authResult, '/');
      } else if (err) {
        console.error(err);
        history.push('/login');
      }
    });
  };

  getAccessToken = () => this.accessToken;

  getIdToken = () => this.idToken;

  setSession = ({ expiresIn, accessToken, idToken }, forward) => {
    // Set isLoggedIn flag in localStorage
    localStorage.setItem('isLoggedIn', 'true');

    // Set the time that the access token will expire at
    const expiresAt = expiresIn * 3600 + new Date().getTime();
    this.accessToken = accessToken;
    this.idToken = idToken;
    this.expiresAt = expiresAt;

    if (forward) {
      return history.replace(forward);
    }
    return history.replace(history.location);
  };

  renewSession = () => {
    this.renewing = true;
    this.auth0.checkSession({}, (err, authResult) => {
      if (authResult && authResult.accessToken && authResult.idToken) {
        this.setSession(authResult);
        this.renewing = false;
      } else if (err) {
        this.clear();
        this.renewing = false;
        history.push('/login');
        console.error(err);
      }
    });
  };

  clear = () => {
    this.accessToken = null;
    this.idToken = null;
    this.expiresAt = 0;
    localStorage.removeItem('isLoggedIn');
  }

  logout = () => {
    // TODO: WHY THE HELL DOESNT RETURNTO WORK??
    const returnTo = '';
    this.auth0.logout({ clientID: this.auth0.clientID, returnTo });
  };

  // Check whether the current time is past the
  // access token's expiry time
  isAuthenticated = () => new Date().getTime() < this.expiresAt;
}

export default new Auth();
