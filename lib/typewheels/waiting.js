const {getTimeoutDate} = require('@vlab-research/utils')
const _ = require('lodash')


function _waitFulfilled(value, events, waitStart) {
  const now = _(events).map(e => new Date(e.value)).max()
  const endDate = getTimeoutDate(waitStart, value)
  return now - endDate >= 0
}

function _equal(v1, v2) {
  return v1 && v2 && _.isEqual(v1, v2)
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

  // to loose? Compare subkey, .value, only???
  return !!relevant.filter(e => _equal(e.value, wait.value)).length
}





module.exports = { waitConditionFulfilled }
