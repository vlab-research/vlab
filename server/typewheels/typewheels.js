
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
    return { ...state, state: 'QOUT', question: nxt.message.metadata.ref }
  }

  else if (nxt.postback && state.state == 'QOUT') {
    const { value, ref } = nxt.postback.payload

    // if postback not related to current question, ignore.
    if (state.question == ref) {
      return { ...state, state: 'QA', response: value }
    }
    return state
  }

  if (state.state == 'QOUT' && nxt.message && nxt.message.text) {
    return {...state, state: 'QA', response: nxt.message.text }
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
