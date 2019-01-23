
// turn logic jumps into referring to ONE response to a sent.
// responses should be ignored if they don't validate with the type of question.

// basically, everything needs to fit into a series of Q:A pairs
// The answer refers to the last Q
// If answer doesn't validate, repeat Q!
// If answer does validate, run through LOGIC JUMPS associated with that Q, to determine next Q
// Send next Q

// one to get vars (in the case of nested op, it should recurse via op)

// one to deal with op

// These need to be recursive in the case of or...

// vars

module.exports = {
  getState,
  getWatermark
}

const {recursiveJSONParser, parseLogJSON, getForm, splitLogsByForm} = require('./utils')
const util = require('util')


// parses all JSON in log...


function getWatermark(event) {
  if (!event.read && !event.delivery) return undefined

  const type = event.read ? 'read' : 'delivery'
  const mark = event[type].watermark

  return {type, mark}
}


function apply(state, nxt) {

  // Update watermark if it's higher
  const {type, mark} = getWatermark(nxt) || {}

  if (mark && !(state[type] > mark)) {
    return {...state, [type]: mark}
  }

  if (nxt.message && nxt.message.is_echo) {

    state = {...state, question: nxt.message.metadata.ref, response: undefined }

    // check for "repeat" state.
    if (nxt.message.metadata.repeat) {
      return {...state, state: 'REPEAT' }
    }

    // statements should be answered immediately
    if (nxt.message.metadata.type === 'statement') {
      return {...state, state: 'QA', valid: true }
    }

    // else there is a question waiting to be answered
    return { ...state, state: 'QOUT' }
  }

  else if (nxt.postback) {
    const { value, ref } = nxt.postback.payload

    // if postback related to current question
    if (state.question === ref && state.state == 'QOUT') {
      return { ...state, state: 'QA', response: value, valid: true }
    }

    // else repeat current question
    // or create QA/valid=false state?
    return {...state, state: 'QA', valid: false}
  }

  // must be a response to a question
  if (state.state === 'QOUT' && nxt.message && nxt.message.text) {
    return {...state, state: 'QA', response: nxt.message.text, valid: undefined }
  }

  // else nothing changes
  return state
}

function getState(log) {
  if (!log || !log.length) {
    throw new TypeError('Attempting to get the state of an empty log!')
  }

  // TODO: remove this from here, get form, currentLog passed in??
  const current = splitLogsByForm(parseLogJSON(log)).pop()

  // no current form, state undefined!
  if (!current) return undefined

  const [form, currentLog] = current
  return currentLog.reduce(apply, { form: form, state: 'START' })
}
