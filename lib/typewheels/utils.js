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
    const r = event.referral || event.postback.referral
    return r.ref.split('.')[0]
  } catch (e) {
    throw new TypeError('getForm can only be called on referral events. Called with: ', event)
  }
}

const _newForm = (prev, nxt, init) => {
  return init ? [...prev, [nxt, [init]]] : [...prev, [nxt, []]]
}

const _addToLastForm = (a,b) => {
  a[a.length - 1][1].push(b)
  return a
}

function _initialSplit(log) {
  return log.reduce((a,b) => {

    // We have a referral, create the associated form
    if (b.referral || (b.postback && b.postback.referral)) {
      return _newForm(a,getForm(b), b)
    }

    // A new user has come via Welcome Screen, with no referral
    if (b.postback && b.postback.payload === 'get_started') {
      return _newForm(a, process.env.FALLBACK_FORM, b)
    }

    // Else event belongs to previous form
    if (a.length) return _addToLastForm(a,b)

    // If, somehow, we have someone chatting with us WITHOUT
    // coming through the welcome screen, but without a referral
    // (as the testers do), we should return the default form
    // also, init handles the case where somehow the logs start
    // with a message from us...
    return _newForm(a, process.env.FALLBACK_FORM, b)
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


module.exports = { recursiveJSONParser, parseLogJSON, getForm, splitLogsByForm }
