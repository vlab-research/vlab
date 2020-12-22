import React, { useEffect, useState } from 'react';
import { useHistory } from 'react-router-dom';
import api from '../../services/api';
import LinkModal from '../../components/LinkModal';

const initFB = (cb) => {
  const appId = process.env.REACT_APP_FACEBOOK_APP_ID;
  const version = '9.0'; // TODO: move to config somewhere!

  // quick hack to check for weird facebook sdk global
  // function that should only be set once
  if (window.FB) {
    return cb();
  }

  window.fbAsyncInit = () => {
    window.FB.init({
      version: `v${version}`,
      appId,
      xfbml: true,
    });

    cb();
  };
};

const loadSDK = () => {
  // code from example: https://developers.facebook.com/docs/facebook-login/web

  function load(d, s, id) {
    const fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)) return;
    const js = d.createElement(s);
    js.id = id;
    js.src = 'https://connect.facebook.net/en_US/sdk.js';
    fjs.parentNode.insertBefore(js, fjs);
  }

  load(document, 'script', 'facebook-jssdk');
};


const fb = (cb) => {
  const cnf = {
    scopes: 'public_profile,email,pages_show_list,pages_messaging,pages_manage_metadata',
    return_scopes: true,
  };

  window.FB.login((res) => {
    const token = res.authResponse.accessToken;

    const body = { token };

    api.fetcher({ path: '/facebook/exchange-token', method: 'POST', body })
      .then(res => res.json())
      .then((res) => {
        if (res.error) throw new Error(res.error);

        const { access_token } = res;

        window.FB.api('/me/accounts', { access_token }, (res) => {
          // TODO: implement paging incase user has many FB pages!
          const response = { pages: res.data, userToken: access_token };
          cb(response);
        });
      })
      .catch(err => console.error(err)); //eslint-disable-line
  }, cnf);
};


const FacebookPages = () => {
  const history = useHistory();
  const back = () => history.go(-1);
  const [pages, setPages] = useState(null);

  useEffect(() => {
    loadSDK();
    initFB(() => {
      fb((res) => {
        setPages(res.pages);
      });
    });
  }, []);

  const callback = async (res) => {
    const { name, id, access_token } = res;
    const body = { entity: 'facebook_page', details: { name, id, access_token } };

    try {
      await api.fetcher({ path: '/credentials', method: 'POST', body });
    } catch (e) {
      console.error(e);
    }
    back();
  };

  return (
    <LinkModal
      title="Connect a Facebook Page"
      initialSelection={{ id: '', name: '' }}
      fallbackText="You don't have any pages! Please first make a Facebook Page to connect it to the bot."
      success={callback}
      loading={pages === null}
      back={back}
      dataSource={pages}
      footer={selected => (
        <LinkModal.s.Selected>
          <LinkModal.s.SelectedInfo>{`selected: ${selected.id}`}</LinkModal.s.SelectedInfo>
          <LinkModal.s.SelectedInfo>{`name: ${selected.name}`}</LinkModal.s.SelectedInfo>
        </LinkModal.s.Selected>
      )}
      renderItem={item => (
        <>
          <LinkModal.s.ListItemTitle>
            {item.name}
          </LinkModal.s.ListItemTitle>
          <LinkModal.s.ListItemId>{item.id}</LinkModal.s.ListItemId>
        </>
      )}

    />
  );
};

FacebookPages.propTypes = {};

export default FacebookPages;
