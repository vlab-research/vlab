const r2 = require('r2')
const gcs = require('./db')

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

  if (res.body && res.body.error) {
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


function _resolve(li, e) {
  if (!li) return [e]

  const i = li.indexOf(e)
  return i === -1 ? [...li, e] : li.slice(0,i+1)

}

class EventStore {
  constructor(db) {
    this.db = db
    this.cache = {}
  }

  async getEvents(user, event) {
    if (this.cache[user]) {
      this.cache[user].push(event)
      return this.cache[user]
    }

    const res = await this.db.get(user)
    const events = _resolve(res, event)
    this.cache[user] = events

    return this.cache[user]
  }
}


module.exports = { getForm, getUser, EventStore, sendMessage, _resolve, gcs };
