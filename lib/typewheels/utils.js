const util = require('util')

function recursiveJSONParser(obj) {
  function traverse(obj) {
    if (typeof obj !== 'object' || obj === null) return obj
    for (let key in obj) {
      obj[key] = recursiveJSONParser(obj[key])
    }
    return obj
  }

  try {
    return traverse(JSON.parse(obj))
  }
  catch (e){
    return traverse(obj)
  }
}

function parseLogJSON(log) {
  return recursiveJSONParser(log)
}

function _group(pairs) {
  const arr = pairs.reduce((a,b,i) => {
      if (i%2) {
      a[a.length-1].push(b)
      return a
    }
    return [...a, [b]]
  }, [])

  const d = {}
  for (let [k,v] of arr) {
    d[k] = v
  }
  return d
}

function _getMetadata(event) {
  try {
    const r = event.referral || event.postback.referral
    const pairs = r.ref.split('.')
    return _group(pairs.map(decodeURIComponent))
  }
  catch (e) {
    // TODO: should only really do this for TypeErrors from referral or ref...
    return {}
  }
}

function getMetadata(log) {
  return _getMetadata(log[0])
}

function getForm(event) {
  const {form} = _getMetadata(event)

  if (!form) {
    throw new TypeError(`Could no find any form for the event: ${util.inspect(event)}`)
  }

  return form
}

const _newForm = (prev, nxt, init) => {
  return [...prev, [nxt, [init]]]
}

const _addToLastForm = (a,b) => {
  a[a.length - 1][1].push(b)
  return a
}

function _initialSplit(log) {
  return log.reduce((a,b) => {

    // We have a referral, create the associated form
    if (b.referral || (b.postback && b.postback.referral)) {
      return _newForm(a, getForm(b), b)
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

// sql get users
// for each user, make sql query
// combine in the end


// splitLogsByForm should give you list of [form,log]
// for each log, form.getLogState --> [Q, [...A]] for each Q
// [Q, [...A]] -> [[Q,A1], [Q,A2]]
// [form, [[Q,A1], [Q,A2]]] -> [[form,Q,A1], [form,Q,A2]]]
// [[form,Q,A1], [form,Q,A2]]] -> [[userid, form,Q,A1], [userid, form,Q,A2]]]
// repeat this for each user id
// write into csv
// expose over http server ?

module.exports = { recursiveJSONParser, parseLogJSON, getForm, splitLogsByForm, _group, getMetadata }
