import React, { useEffect, useState } from 'react';
import { useHistory, useLocation } from 'react-router-dom';
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


const getPages = (access_token, limit, after) => new Promise((resolve, reject) => {
  const params = { access_token, limit, after };

  window.FB.api('/me/accounts', params, (res) => {
    if (res.error) return reject(res.error);
    return resolve(res);
  });
});

const fb = (cb) => {
  const cnf = {
    scope: 'public_profile,email,pages_show_list,pages_messaging,pages_manage_metadata',
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
        return getPages(access_token, 3).then(result => ({ result, access_token }));
      })
      .then(cb)
      .catch(err => console.error(err)); //eslint-disable-line
  }, cnf);
};


const FacebookPages = () => {
  // modify to work for create and update igual

  const history = useHistory();
  const location = useLocation();
  const query = new URLSearchParams(location.search);

  const back = () => history.go(-1);
  const [pages, setPages] = useState(null);

  const key = query.get('key');


  const handle = async (res) => {
    const e = await res.json();

    if (res.status === 400) {
      if (e.code === '23505') {
        alert('You (or someone else in a different account) already connected this Page. You can use the "update" link to update the credentials.');
        return;
      }
    }

    throw new Error(JSON.stringify(e));
  };

  const formatPage = (res) => {
    const { name, id, access_token } = res;
    return { entity: 'facebook_page', key: id, details: { name, id, access_token } };
  };

  const addWebhook = async cred => api.fetcher({
    path: '/facebook/webhooks',
    method: 'POST',
    body: {
      pageid: cred.details.id,
      token: cred.details.access_token,
    },
  });

  const addGetStarted = async cred => api.fetcher({
    path: '/facebook/get-started',
    method: 'POST',
    body: {
      pageid: cred.details.id,
      token: cred.details.access_token,
    },
  });

  const callback = async (res) => {
    const body = formatPage(res);

    try {
      const res = await api.fetcher({
        path: '/credentials', method: 'POST', body, raw: true,
      });

      if (!res.ok) {
        await handle(res);
        return;
      }
      const cred = await res.json();
      await addWebhook(cred);
      await addGetStarted(cred);
    } catch (e) {
      console.error(e);
      alert(e);
    }
    back();
  };

  const update = async (page) => {
    try {
      const res = await api.fetcher({ path: '/credentials', method: 'PUT', body: formatPage(page) });
      const cred = await res.json();
      await addWebhook(cred);
      await addGetStarted(cred);
      alert(`Page ID ${cred.key} credentials have been updated succesfully.`);
    } catch (e) {
      console.error(e);
      alert(e);
    }

    back();
  };

  useEffect(() => {
    loadSDK();
    initFB(() => {
      fb((res) => {
        setPages(res.result.data);

        // TODO: build UI to page though pages.
        // getPages(res.access_token, 3, res.result.paging.cursors.after).then(console.log);
      });
    });
  }, []);

  if (pages && key) {
    const p = pages.find(p => p.id === key);
    if (p) {
      update(p);
      return null;
    }
  }


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
