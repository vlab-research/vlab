const {recursiveJSONParser, getPageFromEvent} = require('@vlab-research/utils')
const farmhash = require('farmhash')
const _ = require('lodash')

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


function randomSeed(event, md) {
  const userId = event.sender.id
  const {form} = md

  if (!form || !userId) return null

  const s = form + userId
  return { seed: farmhash.fingerprint32(s) }
}

function getMetadata(event) {
  let md

  try {

    const r = event.referral ||
          _.get(event, ['postback', 'referral']) ||
          _.get(event, ['postback', 'payload', 'referral']) ||
          _.get(event, ['message', 'quick_reply', 'payload', 'referral'])

    const pairs = r.ref.split('.')
    md = _group(pairs.map(decodeURIComponent))

  }
  catch (e) {
    // TODO: should only really do this for TypeErrors from referral or ref...
    md = {}
  }

  md.form = md.form || process.env.FALLBACK_FORM
  md.startTime = event.timestamp
  md.pageid = getPageFromEvent(event)

  return {...md,
          ...randomSeed(event, md)}
}

function getForm(event) {
  const {form} = getMetadata(event)
  return form
}



module.exports = {
  recursiveJSONParser,
  parseLogJSON,
  getForm,
  _group,
  getMetadata }
