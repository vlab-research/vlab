const util = require('util')
const {recursiveJSONParser} = require('@vlab-research/utils')

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

function getMetadata(event) {
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

function getForm(event) {
  const {form} = getMetadata(event)
  return form ? form : process.env.FALLBACK_FORM
}



module.exports = {
  recursiveJSONParser,
  parseLogJSON,
  getForm,
  _group,
  getMetadata }
