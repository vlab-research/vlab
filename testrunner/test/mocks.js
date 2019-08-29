// https://m.me/testvirtuallab?ref=form.LDfNCy
const uuid = require('uuid');
const PAGE_ID = '935593143497601';

const {translator, addCustomType} = require('@vlab-research/translate-typeform')
const fs = require('fs')

function getFields(path) {
  const form = JSON.parse(fs.readFileSync(path, 'utf-8'))
  return form.fields.map(addCustomType).map(translator)
}

function makeReferral(userId, formId) {
  return {
    id: PAGE_ID,
    time: Date.now(),
    messaging:[
      { recipient: { id: PAGE_ID },
        timestamp: Date.now(),
        sender: { id: userId },
        referral: {
          ref: `form.${formId}`,
          source: 'SHORTLINK',
          type: 'OPEN_THREAD' } } ]
  }
}

function _baseMessage(userId, extra) {
  return {
    id: uuid(),
    time: Date.now(),
    messaging: [{
      sender: { id: PAGE_ID } ,
      recipient: { id: userId },
      timestamp: Date.now(),
      ...extra
    }]
  }
}

function makeEcho(message, userId) {
  const extra =  {
    message: {
      is_echo: true,
      metadata: message.metadata,
      text: message.text || message.attachment.payload.text,
    }
  }

  return _baseMessage(userId, extra)
}

function makePostback(message, userId, idx) {

  const button = message.attachment.payload.buttons[idx]
  const postback = {payload: button.payload, title: button.title }

  return _baseMessage(userId, {postback})
}

function makeTextResponse(userId, text) {
  return _baseMessage(userId, { message: { text }})
}

module.exports = {
  makeReferral,
  makeEcho,
  makePostback,
  makeTextResponse,
  getFields
}
