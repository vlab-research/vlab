const fb = require('../../config').FACEBOOK;
const r2 = require('r2');


exports.exchangeToken = async (req, res) => {
  const {token} = req.body;

  const url = `${fb.url}/oauth/access_token?grant_type=fb_exchange_token&client_id=${fb.id}&client_secret=${fb.secret}&fb_exchange_token=${token}`

  const r = await r2.get(url).json;

  if (r.error) {
    // TODO: put into general error handling (next)
    console.error(r.error);
    return res.status(400).json(r.error);
  }

  return res.json({ access_token: r.access_token });
}

exports.addWebhooks = async (req, res) => {
  const {pageid, token} = req.body;

  const json = {
    subscribed_fields: ['messages',
                        'messaging_postbacks',
                        'messaging_optins',
                        'messaging_account_linking',
                        'messaging_referrals',
                        'message_echoes',
                        'messaging_handovers',
                        'messaging_policy_enforcement']
  }

  const url = `https://graph.facebook.com/v9.0/${pageid}/subscribed_apps?access_token=${token}`
  const r = await r2.post(url, { json }).json

  if (r.error) {
    // TODO: put into general error handling (next)
    console.error(r.error);
    return res.status(400).json(r.error);
  }

  return res.status(201).json(r);
}
