const r2 = require('r2')

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

async function sendMessage(recipientId, response) {
  const headers = { Authorization: `Bearer ${process.env.PAGE_ACCESS_TOKEN}`}
  const json = {
    recipient: { id: recipientId },
    message: response
  }

  const url = 'https://graph.facebook.com/v3.2/me/messages'
  const res = await r2.post(url, { headers, json })

  if (res.body && res.body.error) {
    throw new Error(res.body.error)
  }

  return res
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

module.exports = {getUser, sendMessage, makeFakeEcho}
