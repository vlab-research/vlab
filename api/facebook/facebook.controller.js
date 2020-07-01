const fb = require('../../config').FACEBOOK;
const r2 = require('r2');


exports.exchangeToken = async (req, res) => {
  const BASE_URL = 'https://graph.facebook.com/v7.0';

  const {token} = req.body;

  const url = `${BASE_URL}/oauth/access_token?grant_type=fb_exchange_token&client_id=${fb.id}&client_secret=${fb.secret}&fb_exchange_token=${token}`

  const r = await r2.get(url).json;

  if (r.error) {
    console.error(r.error);
    return res.status(500).json(r.error);
  }

  return res.json({ access_token: r.access_token });
}
