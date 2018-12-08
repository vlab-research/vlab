const fs = require('fs')
const util = require('util')
const request = require('request')
require('dotenv').config()

const readFile = util.promisify(fs.readFile)

const {Machine} = require('./typewheels/form')
const {getState} = require('./typewheels/typewheels')

const verifyToken = (ctx) => {
  if (ctx.query['hub.verify_token'] === process.env.VERIFY_TOKEN) {
    ctx.body = ctx.query['hub.challenge']
    ctx.status = 200
  } else {
    ctx.body = 'invalid verify token'
    ctx.status = 401
  }
}

function shareButton(title, url) {
  return {
    "type": "element_share",
    "share_contents": {
      "attachment": {
        "type": "template",
        "payload": {
          "template_type": "generic",
          "elements": [
            {
              "title": title,
              // "subtitle": "<TEMPLATE_SUBTITLE>",
              // "image_url": "<IMAGE_URL_TO_DISPLAY>",
              "default_action": {
                "type": "web_url",
                "url": url
              },
              "buttons": [
                {
                  "type": "web_url",
                  "url": url,
                  "title": title
                }
              ]
            }
          ]
        }
      }
    }
  }
}

function shareMessage(title, url) {
  return {
    "attachment":{
      "type":"template",
      "payload":{
        "template_type":"button",
        "text": "Do you wish to share this?",
        "buttons": [ shareButton(title, url)]
      }
    },
    metadata: '{ "ref": "foobarbaz"}' // Get the ref from the question
  }
}

const farmhash = require('farmhash')

async function sendMessage(recipientId, response, redis) {

  // quick hack to avoid double sending!
  const i = farmhash.hash32(JSON.stringify(response))
  if (await redis.exists(`sent:${i}`)) return
  await redis.set(`sent:${i}`, true, 'EX', 10)

  request({
    url: 'https://graph.facebook.com/v3.2/me/messages',
    headers: { Authorization: `Bearer ${process.env.PAGE_ACCESS_TOKEN}`},
    method: 'POST',
    json: {
      recipient: { id: recipientId },
      message: response,
    }
  }, function (error, response, body) {
    if (error) {
      console.log('Error sending message: ', error);
    } else if (response.body.error) {
      console.log('Error: ', response.body.error);
    }
  })
}



// One function goes through, and picks up the last referral
// From there, it plays the events against the "form" that corresponds to that referral
// From each recieved answer, given the form, it decides what answer to send
// If that answer is already sent, it plays the next recieved
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



function getUser(event) {
  const PAGE_ID = process.env.FBPAGE_ID

  if (event.sender.id == PAGE_ID) {
    return event.recipient.id
  }
  else if (event.recipient.id == PAGE_ID){
    return event.sender.id
  }
  else {
    // TODO: make error
    throw new Error('Non Existent User!')
  }
}

var Redis = require('ioredis')
var redis = new Redis()

var Cacheman = require('cacheman')
var cache = new Cacheman()

const getFormCached = form => cache.wrap('form', () => getForm(form), '30s')

const processed = {}

const startSurvey = async (ctx) => {
  console.log('>>>>>>>>> REQUEST <<<<<<<<<<<<<<<<<')
  for (entry of ctx.request.body.entry) {
    try {
      console.log('+++ ENTRY: ', entry)

      // TODO: change to use Redis as queue
      // and move sending to another service that does queue processing!
      // thus we remove race conditions

      const event = entry.messaging[0]
      const user = getUser(event)
      const machine = new Machine()

      await redis.lpush(user, JSON.stringify(event))
      const r = await redis.lrange(user, 0, -1)
      r.reverse()
      const log = r.map(JSON.parse)
      const state = getState(log)

      if (!state) throw new Error('User does not have any current form!')

      const form = await getFormCached(state.form)
      const action = machine.exec(state, form, log)

      if (action) {
        await sendMessage(user, action, redis)
      }
    } catch (error) {
      console.error('[ERR] startSurvey: ', error)
    }
  }
  ctx.status = 200
}

module.exports = {
  verifyToken,
  startSurvey
}
