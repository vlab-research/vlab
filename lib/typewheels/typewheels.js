const {recursiveJSONParser, parseLogJSON, splitLogsByForm} = require('./utils')
const util = require('util')

function getWatermark(event) {
  if (!event.read && !event.delivery) return undefined

  const type = event.read ? 'read' : 'delivery'
  const mark = event[type].watermark

  return {type, mark}
}

const _is_echo = n => n.message && n.message.is_echo

function apply(state, nxt) {

  // Update watermark if it's higher
  const {type, mark} = getWatermark(nxt) || {}

  if (mark && !(state[type] > mark)) {
    return {...state, [type]: mark}
  }

  if (_is_echo(nxt)) {

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

    // if it's not, it's an invalid postback:
    return {...state, state: 'QA', valid: false}
  }

  // must be a response to a question
  if (state.state === 'QOUT' && nxt.message && nxt.message.text) {
    return {...state, state: 'QA', response: nxt.message.text, valid: undefined }
  }

  // a second answer, or an answer to a statement!
  // we should validate it
  if (state.state === 'QA' && nxt.message && nxt.message.text) {
    return {...state, state: 'QA', response: nxt.message.text, valid: undefined }
  }

  // else nothing changes
  return state
}

function resolveFakeEchos(log) {
  // removes any echos that are already "faked"

  const fakes = log
        .filter(e => e.message && e.message.fake_echo)
        .map(e => e.message.metadata.ref)

  const is_faked = e => fakes.find(echo => echo === e.message.metadata.ref)
  const is_echo = e => (e.message && e.message.is_echo && !e.message.fake_echo)

  return log
    .filter(e => (!is_echo(e) || !is_faked(e)))
}

function getCurrentForm(log) {
  const current = splitLogsByForm(parseLogJSON(log)).pop()
  const [form, currentLog] = current || [undefined, undefined]

  return [form, resolveFakeEchos(currentLog)]
}

function getState(log) {
  if (!log || !log.length) {
    throw new TypeError('Attempting to get the state of an empty log!')
  }

  const [form, currentLog] = getCurrentForm(log)
  return currentLog.reduce(apply, { form, state: 'START' })
}

module.exports = {
  getState,
  getWatermark,
  resolveFakeEchos
}
