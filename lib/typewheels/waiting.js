const _ = require('lodash')
const parse = require('parse-duration')
const {getTimeoutDate} = require('@vlab-research/utils')


function _waitFulfilled(value, events, waitStart) {
  const now = _(events).map(e => new Date(e.value)).max()
  const endDateV1 = getTimeoutDate(waitStart, value)
  const endDateV2 = new Date(waitStart + parse(value))

  // NOTE: this needs to work for 3 different versions
  // right now, which can be simplified in the future
  const fulfilled = _(events).map(e => e.value).includes(waitStart)
  return fulfilled || (now - endDateV2 >= 0) || (now - endDateV1 >= 0)
}

const _contains = (a, b) => _.keys(b).every(k => a[k] === b[k])

function _matches(v1, v2) {
  return v1 && v2 && (_.isEqual(v1, v2) || _contains(v1, v2))
}

const funs = {
  'and': (...args) => args.reduce((a,b) => a && b, true),
  'or': (...args) => args.reduce((a,b) => a || b, false)
}

function waitConditionFulfilled(wait, events, waitStart) {

  const {type, value, op, vars} = wait

  if (op) {
    const fn = funs[op]
    return fn(...vars.map(w => waitConditionFulfilled(w, events, waitStart)))
  }

  const relevant = events
        .map(e => e.event)
        .filter(e => e.type === type)

  if (type === 'timeout') {
    return _waitFulfilled(value, relevant, waitStart)
  }

  return relevant.some(e => _matches(e.value, wait.value))
}


module.exports = { waitConditionFulfilled }
