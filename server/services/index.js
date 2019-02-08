const r2 = require('r2')

function translateForm(form) {
  const f = {...form}
  f.fields = [...f.fields, ...f.thankyou_screens.map(s => ({...s, type: 'thankyou_screen'}))]
  return f
}

async function getForm(form) {
  const headers = {Authorization: `Bearer ${process.env.TYPEFORM_KEY}`}
  const res = await r2(`https://api.typeform.com/forms/${form}`, {headers}).response
  const f = await res.json()
  return translateForm(f)
}

async function sendMessage(recipientId, response) {
  const headers = { Authorization: `Bearer ${process.env.PAGE_ACCESS_TOKEN}`}
  const json = {
    recipient: { id: recipientId },
    message: response
  }

  const url = 'https://graph.facebook.com/v3.2/me/messages'
  const res = await r2.post(url, { headers, json })

  if (res.body.error) {
    throw new Error(res.body.error)
  }

  return res
}

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


const db = {}

async function getEvents(user, event) {
  if (db[user]) {
    db[user].push(event)
    return db[user]
  }
  // get from filestore !
  // check if event is duplicate - race from other consumer
  db[user] = [event]
  return db[user]
}

module.exports = { getForm, getUser, getEvents, sendMessage };
