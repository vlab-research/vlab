import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import api from '../../services/api';

const initFB = () => {
  const appId = process.env.REACT_APP_FACEBOOK_APP_ID;
  const version = '9.0'; // TODO: move to config somewhere!

  window.fbAsyncInit = () => {
    window.FB.init({
      version: `v${version}`,
      appId,
      xfbml: true,
    });
  };
};

const loadSDK = () => {
  // code from example: https://developers.facebook.com/docs/facebook-login/web

  function load (d, s, id) {
    const fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)) return;
    const js = d.createElement(s);
    js.id = id;
    js.src = 'https://connect.facebook.net/en_US/sdk.js';
    fjs.parentNode.insertBefore(js, fjs);
  };

  load(document, 'script', 'facebook-jssdk');
};


const fb = (cb) => {
  const cnf = { scopes: 'public_profile,email,pages_show_list,pages_messaging',
                return_scopes: true };

  window.FB.login(res => {

    const token = res.authResponse.accessToken;

    const body = { token };

    api.fetcher({path: '/facebook/exchange-token', method: 'POST', body })
      .then(res => res.json())
      .then(res => {
        if (res.error) throw new Error(res.error);

        const {access_token} = res;

        window.FB.api('/me/accounts', {access_token}, res => {
          // TODO: implement paging incase user has many FB pages!
          const response = { pages: res.data, userToken: access_token };
          cb(response);
        });
      })
      .catch(err => console.error(err)); //eslint-disable-line

  }, {scopes: 'public_profile,email,pages_show_list,pages_messaging,pages_manage_metadata,ads_management', return_scopes: true});
};


// callback will be given a list of "pages" from the FB API
const FacebookPages = ({ callback }) => {
  useEffect(() => {
    initFB();
    loadSDK();
  });

  // TODO style button
  return (
    <div>
      <button onClick={() => fb(callback)}>Connect Facebook</button>
    </div>
  );
};

FacebookPages.propTypes = {
  callback: PropTypes.func.isRequired,
};

export default FacebookPages;
