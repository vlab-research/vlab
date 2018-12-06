module.exports = { recursiveJSONParser, parseLogJSON, getForm, splitLogsByForm }

function recursiveJSONParser(obj) {
  try {
    return JSON.parse(obj)
  }
  catch (e){
    if (typeof obj !== 'object' || obj === null) return obj
    for (let key in obj) {
      obj[key] = recursiveJSONParser(obj[key])
    }
    return obj
  }
}

function parseLogJSON(log) {
  return recursiveJSONParser(log)
}

function getForm(event) {
  try {
    return event.referral.ref.split('.')[0] // TODO: come up with format to get form!
  } catch (e) {
    throw new TypeError('getForm can only be called on referral events. Called with: ', event)
  }
}

const _newForm = (a,b) => [...a, [getForm(b), []]]

const _addToLastForm = (a,b) => {
  a[a.length - 1][1].push(b)
  return a
}

function _initialSplit(log) {
  return log.reduce((a,b) => {
    if (b.referral) return _newForm(a,b)
    if (a.length) return _addToLastForm(a,b)
    return a
  }, [])
}

function _combineSplits(split) {
  return split.reduce((a,b) => {
    const last = a[a.length - 1]

    if (last && last[0] == b[0]) {
      last[1] = [...last[1], ...b[1]]
      return a
    }

    return [...a, b]
  }, [])
}

function splitLogsByForm(log) {
  const split = _initialSplit(log)
  return _combineSplits(split)
}
