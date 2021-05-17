const r2 = require('r2')

const BOTSERVER_URL = process.env.BOTSERVER_URL || 'http://localhost:3000';

const sendMessage = async function (message) {
  let json, url
  const {source} = message

  switch (source) {

  case 'synthetic':
    url = `${BOTSERVER_URL}/synthetic`
    json = message
    break

  default:
    url = `${BOTSERVER_URL}/webhooks`
    json = { entry: [message] }
  }

  const res = await r2.post(url, { json }).response;

  if (res.body && res.body.error) {
    throw new Error(res.body.error);
  }
  return res;
};

module.exports = sendMessage;
