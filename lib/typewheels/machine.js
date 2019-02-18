const {recursiveJSONParser, parseLogJSON, splitLogsByForm} = require('./utils')
const {translator, validator}= require('../translate-typeform')
const {getField, getNextField } = require('./form')
const r2 = require('r2')


function repeatResponse(question, text) {
  if (!text) {
    throw new TypeError(`Repeat response attempted without valid text: ${question}` )
  }

  return {
    text,
    metadata: JSON.stringify({ repeat: true, ref: question })
  }
}

function getWatermark(event) {
  if (!event.read && !event.delivery) return undefined

  const type = event.read ? 'read' : 'delivery'
  const mark = event[type].watermark

  return {type, mark}
}



function exec (state, nxt) {
  const {type, mark} = getWatermark(nxt) || {}

  if (state.state === 'START') {
    return { action: 'RESPOND' }
  }

  if (mark && !(state[type] > mark)) {
    return { action: 'WATERMARK', update: {[type]: mark} }
  }

  if (nxt.message && nxt.message.is_echo) {

    if (nxt.message.metadata.repeat) {
      return { action: 'SEND_QUESTION', question: state.question }
    }

    if (nxt.message.metadata.type === 'statement') {
      return { action: 'RESPOND',
               validation: {valid: true},
               question: nxt.message.metadata.ref }
    }

    return { action: 'WAIT_RESPONSE', question: nxt.message.metadata.ref }
  }

  else if (nxt.postback) {
    const { value, ref } = nxt.postback.payload

    // If it is a postback to the current question, it's valid
    if (state.question === ref && state.state == 'QOUT') {
      return { action: 'RESPOND',
               validation: { valid: true},
               response: value,
               question: state.question }
    }

    // otherwise, it's invalid
    return { action: 'RESPOND',
             validation: {valid: false,
                          message: 'Please respond to the question:'},
             question: state.question }
  }

  // Must be something from user, validate it against our last outstanding question
  if (nxt.message && nxt.message.text) {
    return { action: 'RESPOND', response: nxt.message.text, question: state.question }
  }
}


function apply (state, output) {
  switch(output.action) {

  case 'WATERMARK':
    return {...state, ...output.update }

  case 'RESPOND':
    return {...state, state: 'RESPONDING', question: output.question || state.question }

  case 'WAIT_RESPONSE':
    return {...state, state: 'QOUT', question: output.question }

  case 'SEND_QUESTION':
    return {...state, state: 'QOUT', question: output.question }
  }
}

function act (state, output, form, log) {
  switch(output.action) {

  case 'RESPOND':
    return respond(output, form, log)

  case 'SEND_QUESTION':
    return translator(getField(form, state.question))

  default:
    return
  }
}

function sendNextQuestion(question, form, log) {
  const field = getNextField(form, log, question)
  return field ? translator(field) : null
}

function respond ({question, validation, response}, form, log) {
  // if we haven't asked anything, it must be the first question!
  if (!question) {
    return translator(form.fields[0])
  }

  // otherwise, validate the response
  const {valid, message} = validation || validator(getField(form, question))(response)

  if (!valid) {
    // Note: this could be abstracted to be more flexible
    return repeatResponse(question, message)
  }
  return sendNextQuestion(question, form, log)
}


function getCurrentForm(log) {
  const current = splitLogsByForm(parseLogJSON(log)).pop()
  const [form, currentLog] = current || [undefined, undefined]

  return [form, currentLog]
}


function getState(log) {
  if (!log || !log.length) {
    return { state: 'START' }
  }

  const [form, currentLog] = getCurrentForm(log)
  return currentLog.reduce((s,e)=> apply(s, exec(s,e)), { state: 'START' })
}

function getMessage(log, form) {
  const event = log.slice(-1)[0]
  const state = getState(log.slice(0,-1))
  const output = exec(state, event)
  return act(state, output, form, log)
}


module.exports = {
  getWatermark,
  getCurrentForm,
  getState,
  exec,
  apply,
  act,
  getMessage
}
