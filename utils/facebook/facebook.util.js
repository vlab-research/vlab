const fb = require('../../config').FACEBOOK;
const r2 = require('r2');

exports.setGetStarted = async (token) => {
  const url = `${fb.url}/me/messenger_profile?access_token=${token}`;

  // TODO: this is term should be in config somewhere!
  // (here and in replybot)
  const json = {get_started:{ payload: 'get_started'}};
  const r = await r2.post(url, { json });
  if (r.error) {
    throw new Error(JSON.stringify(r.error))
  }
}

exports.subscribe = async (page, token)  => {
  const url = `${fb.url}/${page}/subscribed_apps?access_token=${token}`;
  const json = { subscribed_fields: ['messages', 
                                     'message_echoes',
                                     'messaging_account_linking', 
                                     'messaging_optins',
                                     'messaging_postbacks',
                                     'messaging_referrals',
                                     'messaging_handovers',
                                     'messaging_fblogin_account_linking',
                                     'messaging_account_linking']}
  const r = await r2.post(url, { json });
  if (r.error) {
    throw new Error(JSON.stringify(r.error))
  }
}
