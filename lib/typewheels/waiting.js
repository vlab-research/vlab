const _ = require('lodash')

function _waitFulfilled(value, events, waitStart) {
  // return true/false
}

function _equal(v1, v2) {
  return v1 && v2 && _.isEqual(v1, v2)
}

function waitConditionFulfilled(wait, events, waitStart) {
  if (wait.operator) {
    return
  }
  // go through wait
  // look for each event from events

  const {type, value} = wait

  const relevant = events
        .map(e => e.event)
        .filter(e => e.type === type)

  if (type === 'timeout') {
    return _waitFulfilled(value, relevant, waitStart)
  }

  // to loose? Compare subkey, .value, only???
  return !!relevant.filter(e => _equal(e.value, wait.value)).length
}


// const ts = chrono.parseDate(value) - Date.now()


module.exports = { waitConditionFulfilled }
