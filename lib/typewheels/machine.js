const util = require('util')
const r2 = require('r2')
const {recursiveJSONParser, parseLogJSON, splitLogsByForm} = require('./utils')
const {translator, validator}= require('../translate-typeform')
const {translateField, getField, getNextField } = require('./form')



function repeatResponse(question, text) {
  if (!text) {
    throw new TypeError(`Repeat response attempted without valid text: ${text}\nquestion: ${question}` )
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


  // If it's the start state, we respond
  // otherwise we ignore all referral events
  if (state.state === 'START') {
    return { action: 'RESPOND' }
  }
  if (nxt.referral) {
    return { action: 'NONE' }
  }

  // Update watermark if it's greater than the
  // current, else ignore it
  if (mark && !(state[type] > mark)) {
    return { action: 'WATERMARK', update: {[type]: mark} }
  }
  if (mark && (state[type] > mark)) {
    return { action: 'NONE' }
  }

  // ECHO
  // TODO METADATA????
  if (nxt.message && nxt.message.is_echo) {

    // If it hasn't been sent by the bot, ignore it
    if (!nxt.message.metadata) {
      return { action: 'NONE' }
    }

    if (nxt.message.metadata.repeat) {
      return { action: 'SEND_QUESTION', question: state.question }
    }


    if (nxt.message.metadata.type === 'thankyou_screen') {
      return { action: 'END', question: nxt.message.metadata.ref }
    }

    // TODO: make statement action: NONE
    // thus, making statements handled on
    // send time
    if (nxt.message.metadata.type === 'statement') {
      return { action: 'RESPOND',
               validation: {valid: true},
               question: nxt.message.metadata.ref }
    }

    return { action: 'WAIT_RESPONSE', question: nxt.message.metadata.ref }
  }

  // If we are in the process of responding,
  // let's not do anything
  // this is dangerous, because if an event wasn't sent,
  // then we will get stuck in "responding" forever
  // ... This should really only happen if
  // Kafka dies, but still it's an edge case worth considering.
  // it's a shame that the offsets is ordered in Kafka, it's really
  // not that great for this actually
  // This would be better served with RabbitMQ, really
  if (state.state === 'RESPONDING') {
    return { action: 'NONE' }
  }

  if (nxt.postback) {
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

  // Quick reply
  if (nxt.message && nxt.message.quick_reply) {
    return { action: 'RESPOND', response: nxt.message.quick_reply.payload.value, question: state.question }
  }

  // Must be something from user, validate it against our last outstanding question
  if (nxt.message && nxt.message.text) {
    return { action: 'RESPOND', response: nxt.message.text, question: state.question }
  }

  // quick hack to invalidate stickers or images
  if (nxt.message && nxt.message.attachments) {
    return { action: 'RESPOND', response: '[STICKER]', question: state.question }
  }

  throw new TypeError(`Machine did not produce output!\nState: ${util.inspect(state, null, 8)}\nEvent: ${util.inspect(nxt, null, 8)}`)
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

  case 'END':
    return {...state, state: 'END', question: output.question }

  default:
    return state
  }
}

function act (ctx, state, output) {
  switch(output.action) {

  case 'RESPOND':
    return respond(ctx, output)

  case 'SEND_QUESTION':
    return translateField(ctx, getField(ctx, state.question))

  default:
    return
  }
}


function sendNextQuestion(ctx, question, previous = []) {

  // TODO: should send multiple questions in case of statement?

  const field = getNextField(ctx, question)
  return field ? translateField(ctx, field) : null

  // if translated.metadata.type === 'statement'
  // recurse with previous = [...previous, translated]
  // else return [...previous, translated]
}

function respond (ctx, {question, validation, response}) {
  // if we haven't asked anything, it must be the first question!
  if (!question) {
    return translateField(ctx, ctx.form.fields[0])
  }

  // otherwise, validate the response
  const {valid, message} = validation ||
        validator(getField(ctx, question), ctx.form.custom_messages)(response)

  if (!valid) {
    // Note: this could be abstracted to be more flexible
    return repeatResponse(question, message)
  }
  return sendNextQuestion(ctx, question)
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

function getMessage(log, form, user) {
  const event = log.slice(-1)[0]
  const state = getState(log.slice(0,-1))
  const output = exec(state, event)
  return act({ log, form, user }, state, output)
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
