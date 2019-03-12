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

  // if (nxt.referral)
  // SWITCH_FORM

  // ECHO
  if (nxt.message && nxt.message.is_echo) {
    const md = nxt.message.metadata

    // If it hasn't been sent by the bot, ignore it
    // If it's a repeat or a statement, ignore it
    if (!md || md.repeat ||
        md.type === 'statement') {
      return { action: 'NONE' }
    }

    if (nxt.message.metadata.type === 'thankyou_screen') {
      return { action: 'END', question: nxt.message.metadata.ref }
    }

    // If we are getting this notification after the
    // delivery notification
    if (nxt.timestamp <= state.delivery) {
      return { action: 'WAIT_RESPONSE',
               question: nxt.message.metadata.ref }
    }

    // Else, we wait for the delivery of this message
    return { action: 'WAIT_DELIVERY',
             question: nxt.message.metadata.ref,
             timestamp: nxt.timestamp }
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
               response: {value, timestamp: nxt.timestamp},
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
    const value = nxt.message.quick_reply.payload.value
    return { action: 'RESPOND',
             response: {value, timestamp: nxt.timestamp},
             question: state.question }
  }


  // Must be something from user, validate it against our last outstanding question
  if (nxt.message && nxt.message.text !== undefined) {
    const value = nxt.message.text
    return { action: 'RESPOND',
             response: {value, timestamp: nxt.timestamp},
             question: state.question }
  }

  // quick hack to invalidate stickers or images
  if (nxt.message && nxt.message.attachments) {
    return { action: 'RESPOND',
             response: {value: '[STICKER]', timestamp: nxt.timestamp},
             question: state.question }
  }

  throw new TypeError(`Machine did not produce output!\nState: ${util.inspect(state, null, 8)}\nEvent: ${util.inspect(nxt, null, 8)}`)
}


function apply (state, output) {
  switch(output.action) {

  case 'WATERMARK':

    // Switch from RESPONDING to QOUT when a question is delivered
    const upd = {...state, ...output.update }
    if (state.state === 'RESPONDING' && upd.delivery >= state.timestamp) {
      return { ...upd, state: 'QOUT' }
    }
    return upd

  case 'RESPOND':
    const qa = updateQA(state.qa, update(output))

    return {...state, state: 'RESPONDING',
            question: output.question,
            qa,
            timestamp: undefined }

  case 'WAIT_DELIVERY':
    return {...state, state: 'RESPONDING',
            question: output.question,
            timestamp: output.timestamp }

  case 'WAIT_RESPONSE':
    return {...state, state: 'QOUT',
            question: output.question }

  case 'END':
    return {...state, state: 'END', question: output.question }

  // case 'SWITCH_FORM':
  //   // add metadata from form
  //   return { ..._initialState(), form: output.form, md: output.md }

  default:
    return state
  }
}

function act (ctx, state, output) {
  switch(output.action) {

  case 'RESPOND':
    const qa = apply(state, output).qa
    return respond(ctx, qa, output)

  default:
    return []
  }
}

function updateQA(qa, u) {
  return u ? [...qa, u] : qa
}

function update ({action, question, response}) {
  if (action === 'RESPOND' && question && response) {
    return [question, response]
  }
}

function nextQuestion(ctx, qa, question) {
  // getNextField should take state?? QA??
  const field = getNextField(ctx, qa, question)
  const msg = field ? translateField(ctx, qa, field) : null
  return msg
}


function _gatherResponses(ctx, qa, q, previous = []) {
  const md = q && JSON.parse(q.metadata)

  if (md.repeat) {
    const repeat = translateField(ctx, qa, getField(ctx, md.ref))
    return [q, repeat]
  }

  if (md.type === 'statement') {
    // if question is statement, recursively
    // get the next question and send it too!
    const nq = nextQuestion(ctx, qa, JSON.parse(q.metadata).ref)
    if (nq) return _gatherResponses(ctx, qa, nq, [...previous, q])
  }

  return [...previous, q]
}

function _response (ctx, qa, {question, validation, response}) {

  // if we haven't asked anything, it must be the first question!
  if (!question) {
    return translateField(ctx, qa, ctx.form.fields[0])
  }

  // otherwise, validate the response
  const {valid, message} = validation ||
        validator(getField(ctx, question), ctx.form.custom_messages)(response.value)

  if (!valid) {
    // Note: this could be abstracted to be more flexible
    // send(repeatResponse(question,message))
    return repeatResponse(question, message)
  }

  return nextQuestion(ctx, qa, question)
}

function respond (ctx, qa, output) {
  return _gatherResponses(ctx, qa, _response(ctx, qa, output)).filter(r => !!r)
}

function getCurrentForm(log) {
  const current = splitLogsByForm(parseLogJSON(log)).pop()
  const [form, currentLog] = current || [undefined, undefined]

  return [form, currentLog]
}

function _initialState() {
  return { state: 'START', qa: [] }
}

function getState(log) {
  if (!log || !log.length) {
    return _initialState()
  }

  return log.reduce((s,e) => apply(s, exec(s,e)), _initialState())
}


function getMessage(log, form, user) {
  const event = log.slice(-1)[0]
  const state = getState(log.slice(0,-1))
  const output = exec(state, event)
  return act({ log, form, user }, state, output)
}

// function getMessage(form, user, state, event) {
//   return act({form, user}, state, exec(state, event))
// }


module.exports = {
  getWatermark,
  getCurrentForm,
  getState,
  exec,
  apply,
  act,
  update,
  getMessage,
  _initialState
}
