const r2 = require('r2')

const BASE_URL = process.env.FACEBOOK_GRAPH_URL || "https://graph.facebook.com/v3.2"
const RETRIES = process.env.FACEBOOK_RETRIES || 5

// Gets user by assuming page ID to be constant.
function getUser(event) {
  const PAGE_ID = process.env.FB_PAGE_ID

  if (event.sender.id === PAGE_ID) {
    return event.recipient.id
  }
  else if (event.recipient.id === PAGE_ID){
    return event.sender.id
  }
  else {
    throw new Error('Non Existent User!')
  }
}

async function facebookRequest(reqFn, retries = 0) {
  let res;

  try {
    res = await reqFn()
  } catch (e) {
    // RETRY ETIMEDOUT ERRORS
    if (e.code === 'ETIMEDOUT' && retries < RETRIES) {
      res = await facebookRequest(reqFn, retries+1)
    } else {
      throw e
    }
  }
  if (res && res.error) {
    throw new Error(JSON.stringify(res.error))
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

function makeFakeEcho(user, action) {
  const us = process.env.FB_PAGE_ID
  const echo = {
    sender: {id: us },
    recipient: {id: user},
    timestamp: Date.now(),
    message: { ...action, fake_echo: true, is_echo: true }
  }
  return JSON.stringify(echo)
}

module.exports = {getUser, sendMessage, makeFakeEcho, getUserInfo}
