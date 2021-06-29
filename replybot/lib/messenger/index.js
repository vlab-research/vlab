const r2 = require('r2')
const {MachineIOError} = require('../errors')
const BASE_URL = process.env.FACEBOOK_GRAPH_URL || "https://graph.facebook.com/v8.0"
const RETRIES = process.env.FACEBOOK_RETRIES || 5

async function facebookRequest(reqFn, retries = 0) {
  let res;

  try {
    res = await reqFn()

  } catch (e) {

    // RETRY ETIMEDOUT ERRORS
    if (e.code === 'ETIMEDOUT' && retries < RETRIES) {
      res = await facebookRequest(reqFn, retries+1)
    }
    else {
      throw new MachineIOError('NETWORK', e.message, { code: e.code, message: e.message })
    }
  }

  if (res && res.error) {

    // TODO: maybe 551 should be removed as it probably won't work on retry?
    const retryCodes = [1200, 551]
    if (retryCodes.includes(res.error.code) && retries < RETRIES) {
      return await facebookRequest(reqFn, retries+1)
    }

    throw new MachineIOError('FB', res.error.message, res.error)
  }

  return res
}


async function getUserInfo(id, pageToken) {
  const url = `${BASE_URL}/${id}?fields=id,name,first_name,last_name`
  const headers = { Authorization: `Bearer ${pageToken}`}

  try {
    const user = await facebookRequest(() => r2.get(url, {headers}).json)
    return user;

  } catch (e) {

    // TODO: we should be removing getUserInfo anyways.
    console.error(e);
    return { id, 'name': '_', first_name: '_', last_name: '_'}
  }
}


async function sendMessage(data, pageToken) {
  const headers = { Authorization: `Bearer ${pageToken}`}
  const url = `${BASE_URL}/me/messages`
  const fn = () => r2.post(url, { headers, json:data }).json
  return await facebookRequest(fn)
}

module.exports = {sendMessage, getUserInfo}
