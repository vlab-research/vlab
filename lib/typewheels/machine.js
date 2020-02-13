const util = require('util')
const r2 = require('r2')
const {getForm, getMetadata, parseLogJSON, splitLogsByForm} = require('./utils')
const {translator, validator}= require('@vlab-research/translate-typeform')
const {translateField, getField, getNextField, addCustomType, interpolateField } = require('./form')
const {waitConditionFulfilled} = require('./waiting')



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

function _currentForm(state) {
  return state.md && state.md.form
}

function _currentUserIsReferrer(event) {
  const md = getMetadata(event)
  return ''+event.sender.id === md.referrer
}

function _externalEvent(event) {
  return event.source === 'synthetic'
}

function categorizeEvent(nxt) {
  if (nxt.referral ||
      (nxt.postback && nxt.postback.referral) ||
      (nxt.postback && nxt.postback.payload === 'get_started')) {
    return 'REFERRAL'
  }

  if (_externalEvent(nxt)) return 'EXTERNAL_EVENT'
  if (getWatermark(nxt)) return 'WATERMARK'
  if (nxt.message && nxt.message.is_echo) return 'ECHO'
  if (nxt.postback) return 'POSTBACK'
  if (nxt.message && nxt.message.quick_reply) return 'QUICK_REPLY'
  if (nxt.message && nxt.message.text !== undefined) return 'TEXT'
  if (nxt.message && nxt.message.attachments) return 'MEDIA'
  if (nxt.reaction) return 'REACTION'

  throw new TypeError(`Machine could not categorize event!
		       \nEvent: ${util.inspect(nxt, null, 8)}`)
}

function _noop() {
  return { action: 'NONE' }
}

function _blankStart(event) {
  return { action: 'SWITCH_FORM',
           form: getForm(event),
           md: getMetadata(event)}
}


function exec (state, nxt) {

  switch(categorizeEvent(nxt)) {

  case 'REFERRAL':
    const form = getForm(nxt)

    // ignore referral to same form
    if (form === _currentForm(state)) return _noop()

    // ignore referral if the person is the referrer
    if (_currentUserIsReferrer(nxt)) return _noop()

    return _blankStart(nxt)


  case 'WATERMARK':
    const {type, mark} = getWatermark(nxt)

    // ignore if mark already higher
    if (state[type] >= mark) return _noop()
    return { action: 'WATERMARK', update: {[type]: mark} }

  case 'EXTERNAL_EVENT':

    if (state.state !== 'WAIT_EXTERNAL_EVENT') {
      return _noop()
    }

    const externalEvents = [...(state.externalEvents || []), nxt]

    if (waitConditionFulfilled(state.wait, externalEvents, state.waitStart)) {
      return { action: 'RESPOND_CANCEL_WAIT',
               question: state.question,
               validation: {valid: true},
               response: null }
    }

    return { action: 'WAIT_EXTERNAL_EVENT',
             question: state.question,
             wait: state.wait,
             waitStart: state.waitStart,
             externalEvents }

  case 'ECHO':
    const md = nxt.message.metadata

    // If it hasn't been sent by the bot, ignore it
    // If it's a repeat or a statement, ignore it
    if (!md || md.repeat || md.type === 'statement') {
      return _noop()
    }

    if (md.type === 'thankyou_screen') {
      return { action: 'END', question: nxt.message.metadata.ref }
    }

    if (md.stitch) {
      // retains metadata (seed)
      // and metadata (form) -- which is the initial form
      return { action: 'SWITCH_FORM', form: md.stitch.form, md: state.md }
    }

    if (md.wait) {
      return { action: 'WAIT_EXTERNAL_EVENT',
               question: md.ref,
               wait: md.wait,
               waitStart: state.waitStart || nxt.timestamp } // propogate if repeat
    }

    // if we receive the echo, we now assume that
    // the user has the question.
    // TODO: simulate problems. Can use timestamps?
    return { action: 'WAIT_RESPONSE',
             question: md.ref }

  case 'POSTBACK':
    if (state.state === 'RESPONDING') return _noop()
    return { action: 'RESPOND',
             response: nxt.postback.payload.value,
             question: state.question }

  case 'QUICK_REPLY':
    if (state.state === 'RESPONDING') return _noop()

    const qrResponse = nxt.message.quick_reply.payload.value === undefined ? nxt.message.quick_reply.payload : nxt.message.quick_reply.payload.value

    return { action: 'RESPOND',
             response:  qrResponse,
             question: state.question }

  case 'TEXT':
    if (state.state === 'RESPONDING') return _noop()

    // Handles the odd case (testers) where they begin
    // texting without any other previous state
    if (state.state === 'START') {
          return _blankStart(nxt)
    }

    return { action: 'RESPOND',
             response: nxt.message.text,
             question: state.question }

  case 'MEDIA':
    if (state.state === 'RESPONDING') return _noop()

    // Handles the odd case (testers) where they begin
    // texting without any other previous state
    if (state.state === 'START') {
      return _blankStart(nxt)
    }

    return { action: 'RESPOND',
             response: '[STICKER]',
             question: state.question }

  case 'REACTION':
    // ignore people "reacting" to messages with emojis and such
    return _noop()

  default:
    throw new TypeError(`Machine did not produce output!\nState: ${util.inspect(state, null, 8)}\nEvent: ${util.inspect(nxt, null, 8)}`)

  }
}


function apply (state, output) {
  switch(output.action) {

  case 'WATERMARK':
    return {...state, ...output.update }

  case 'RESPOND':
    return {...state,
            state: 'RESPONDING',
            question: output.question,
            qa: updateQA(state.qa, update(output))}

  case 'RESPOND_CANCEL_WAIT':
    return {...state,
            state: 'RESPONDING',
            question: output.question,
            wait: null,
            waitStart: null,
            qa: updateQA(state.qa, update(output)) }

  case 'SWITCH_FORM':
    return { ..._initialState(),
             state: 'RESPONDING',
             forms: [...state.forms, output.form],
             md: output.md }

  case 'WAIT_RESPONSE':
    return {...state, state: 'QOUT',
            question: output.question }

  case 'WAIT_EXTERNAL_EVENT':
    return {...state,
            state: 'WAIT_EXTERNAL_EVENT',
            question: output.question,
            wait: output.wait,
            externalEvents: output.externalEvents || state.externalEvents,
            waitStart: output.waitStart}

  case 'END':
    return {...state, state: 'END', question: output.question }

  default:
    return state
  }
}

function act (ctx, state, output) {
  let qa

  switch(output.action) {

  case 'RESPOND':
    qa = apply(state, output).qa
    return respond({...ctx, md: state.md}, qa, output)

  case 'RESPOND_CANCEL_WAIT':
    qa = apply(state, output).qa
    return respond({...ctx, md: state.md}, qa, output)

  case 'SWITCH_FORM':
    return respond({...ctx, md: output.md}, [], output)

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
  const field = getNextField(ctx, qa, question)
  return field ? translateField(ctx, qa, field) : null
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
    const nq = nextQuestion(ctx, qa, md.ref)
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
        // add interpolation and customTypes to field given to validator...
        validator(addCustomType(interpolateField(ctx, qa, getField(ctx, question))),
                  ctx.form.custom_messages)(response)

  if (!valid) {
    // Note: this could be abstracted to be more flexible
    return repeatResponse(question, message)
  }

  return nextQuestion(ctx, qa, question)
}

function respond (ctx, qa, output) {
  return _gatherResponses(ctx, qa, _response(ctx, qa, output)).filter(r => !!r)
}

function _initialState() {
  return { state: 'START', qa: [], forms: [] }
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
  return act({form, user}, state, exec(state, event))
}



module.exports = {
  getWatermark,
  getState,
  exec,
  apply,
  act,
  update,
  getMessage,
  _initialState
}
