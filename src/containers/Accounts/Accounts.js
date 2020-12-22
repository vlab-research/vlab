import React from 'react';
import { List, Divider } from 'antd';
import { Hook } from '../../services';
import { groupBy } from '../../helpers';
import { CreateBtn } from '../../components/UI';

const accountConfs = [
  {
    to: '/connect/facebook-messenger',
    title: 'Facebook Messenger',
    entity: 'facebook_page',
    description: 'To use the Virtual Lab chatbot, Connect your Facebook account and grant Virtual Lab permission to manage messages for the Page for which you are the administrator. Virtual Lab will have permission to send and receieve messages on the behalf of the Page',
  },
  {
    to: '/connect/facebook-ads',
    title: 'Facebook Advertising',
    entity: 'facebook_ad_user',
    description: 'To use the Virtual Lab ad optimization with Facebook Advertising, Connect your Facebook account and grant Virtual Lab permission to manage ads on your behalf. ',
  },
];

const Accounts = () => {
  const accounts = Hook.useMountFetch({ path: '/credentials' }, null)[0];

  if (accounts === null) {
    return null;
  }

  const a = groupBy(accounts, a => a.entity);
  const confs = accountConfs.map((acc) => {
    const r = a.get(acc.entity);
    if (!r) return acc;

    // TODO: make this a function from confs
    return { ...acc, connected: r[0].details.name };
  });

  return (
    <>
      <div className="accounts" style={{ maxWidth: 1000, margin: '2em auto' }}>
        <h1 style={{}}> Connected Accounts </h1>
        <List
          dataSource={confs}
          renderItem={item => (
            <>
              <List.Item
                actions={[<CreateBtn key={1} selected={!!item.connected} to={item.to}>
                  {item.connected || 'CONNECT'}
                          </CreateBtn>,
                ]}
              >
                <List.Item.Meta
                  title={item.title}
                  description={item.description}
                />

              </List.Item>
              <Divider />
            </>
          )}
        />
      </div>
    </>
  );
};

Accounts.propTypes = {};

export default Accounts;
