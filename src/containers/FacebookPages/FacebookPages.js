import React, {useEffect} from 'react';
import PropTypes from 'prop-types';

const initFB = () => {
  const appId = process.env.REACT_APP_FACEBOOK_APP_ID;
  const version = '7.0'; // TODO: move to config somewhere!

  window.fbAsyncInit = () => {
    window.FB.init({
      version: `v${version}`,
      appId,
      xfbml: true,
    });
  };
}

const loadSDK = () => {
  // code from example: https://developers.facebook.com/docs/facebook-login/web

  function load (d, s, id) { 
    var js, fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)) return;
    js = d.createElement(s); js.id = id;
    js.src = "https://connect.facebook.net/en_US/sdk.js";
    fjs.parentNode.insertBefore(js, fjs);
  }

  load(document, 'script', 'facebook-jssdk');
}


const fb = (cb) => {

  window.FB.login(res => {
    window.FB.api('/me/accounts', res => {

      // TODO: implement paging incase user has many FB pages!
      cb(res.data);
    });

  }, {scopes: 'public_profile,email,pages_show_list', return_scopes: true});
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
