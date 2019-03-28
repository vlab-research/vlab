const r2 = require('r2')

const BOTSERVER_URL = process.env.BOTSERVER_URL || 'http://localhost:3000';

const sendMessage = async function (message) {
  const json = {
    entry: [message]
  }

  const url = `${BOTSERVER_URL}/webhooks`;
  const res = await r2.post(url, { json }).response;

  if (res.body && res.body.error) {
    throw new Error(res.body.error);
  }
  return res;
};

module.exports = sendMessage;