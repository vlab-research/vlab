const r2 = require('r2')

const BASE_URL = process.env.FACEBOOK_GRAPH_URL || "https://graph.facebook.com/v3.2"
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
      throw e
    }
  }

  if (res && res.error) {

    // TODO: test the follow error type!
    // {"message":"(#551) This person isn't available right now.","type":"OAuthException","code":551,"error_subcode":1545041,"fbtrace_id":"A-uGilvKq2J3LiGxfi3p2e4"} //
    const retryCodes = [1200, 551]
    if (retryCodes.includes(res.error.code) && retries < RETRIES) {
      res = await facebookRequest(reqFn, retries+1)
    }
    else {
      throw new Error(JSON.stringify(res.error))
    }

  }

  return res
}

async function getUserInfo(id) {
  const url = `${BASE_URL}/${id}?fields=id,name,first_name,last_name`
  const headers = { Authorization: `Bearer ${process.env.PAGE_ACCESS_TOKEN}`}
  try {
    return await facebookRequest(() => r2.get(url, {headers}).json)
  }
  catch (e) {
    console.warn(`Error fetching user information for user: ${id}\n with Error code: ${e.code}\n and error: ${e}`)
    return {}
  }
}

async function sendMessage(recipientId, response, retries = 0) {
  const headers = { Authorization: `Bearer ${process.env.PAGE_ACCESS_TOKEN}`}
  const json = {
    recipient: { id: recipientId },
    message: response
  }
  const url = `${BASE_URL}/me/messages`
  const fn = () => r2.post(url, { headers, json }).json
  return await facebookRequest(fn)
}

module.exports = {sendMessage, getUserInfo}
