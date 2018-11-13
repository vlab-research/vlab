const fs = require('fs')
const util = require('util')
const request = require('request')
require('dotenv').config()

const readFile = util.promisify(fs.readFile)

let translatedForm
let counter = 0
const answers = []

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
    metadata: 'foobarbaz'
  }
}

function sendMessage(recipientId, response) {
  request({
    url: 'https://graph.facebook.com/v3.1/me/messages',
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


// const addQuestion = (question) => {
//   answers[counter] = {question}
// }

// const saveReply = (answer) => {
//   if (answers[counter - 1]) answers[counter - 1].answer = answer
// }

// const handleMessage = (event, translatedForm) => {
//   let sender_psid = event.sender.id
//   if (counter === 0) {
//     sendMessage(sender_psid, translatedForm[counter])
//     counter ++
//   } else if (counter === 1) {
//     addQuestion(translatedForm[counter].title)
//     sendMessage(sender_psid, translatedForm[counter])
//     counter++
//   } else if (translatedForm[counter]) {
//     saveReply(event.message.text)
//     addQuestion(translatedForm[counter].title)
//     sendMessage(sender_psid, translatedForm[counter])
//     counter ++
//   }
// }

const handlePostback = (event, questions) => {
  console.log(event)
}

// id:
// type: sent
// message: #ID

// id:
// type: response
// message: text

// id:
// type: referral
// ???


// One function goes through, and picks up the last referral
// From there, it plays the events against the "form" that corresponds to that referral
// From each recieved answer, given the form, it decides what answer to send
// If that answer is already sent, it plays the next recieved
const r2 = require('r2')

// const util = require('util')
async function getForm() {
  const headers = {Authorization: `Bearer ${process.env.TYPEFORM_KEY}`}
  const res = await r2('https://api.typeform.com/forms/ODf5n7', {headers}).response
  return await res.json()
}


async function foo() {
  const headers = { Authorization: `Bearer ${process.env.PAGE_ACCESS_TOKEN}`}
  const res = await r2('https://graph.facebook.com/v3.1/me/conversations', {headers}).response
  return await res.json()
}





// foo().then(res => console.log(res))

const PAGE_ID = 1051551461692797

function getUser(event) {
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

var Redis = require('ioredis');
var redis = new Redis();

redis.lrange('1800244896727776', 0, -1).then(r => {
  // console.log(r.map(JSON.parse))
  // const l = r.map(JSON.parse)
  // fs.writeFileSync('foo.json', JSON.stringify(l, null, 4))
})


const startSurvey = async (ctx) => {

  try {
    const body = ctx.request.body

    // const form = await getForm()

    // if (!translatedForm) translatedForm = translateForm(form)
    if (body.object === 'page') {
      body.entry.forEach((entry) => {
        const event = entry.messaging[0]
        const user = getUser(event)

        redis.lpush(user, JSON.stringify(event))
        console.log('EVENT: ', event)
        // handle read event?

        if (event.delivery) {
          // handle delivery?
        }

        if (event.referral) {
          console.log('REFERRAL: ', event.referral)
          const refs = event.referral.ref.split('.')
          console.log('refs: ', refs)
        }

        if (event.message && !event.message.is_echo) {
          console.log('MESSAGE: ', event.message)
          sendMessage(user, shareMessage('Take the quiz!', 'https://m.me/betaproject2?ref=NANDAN.rao.hello.ok'))
        //   // handleMessage(event, translatedForm)
        } else if (event.postback && event.postback.payload) {
          console.log('POSTBACK: ', event.postback)
        //   // let payload = received_postback.payload
        //   // handlePostback(payload, questions)
        }
        ctx.status = 200
      })
    } else {
      ctx.status = 404
    }
  } catch (error) {
    console.error('[ERR] startSurvey: ', error)
  }
}

module.exports = {
  verifyToken,
  startSurvey
}
