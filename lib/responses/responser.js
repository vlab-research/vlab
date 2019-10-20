const Cacheman = require('cacheman')
const {exec, apply, update} = require('../typewheels/machine')
const {getField, FieldError} = require('../typewheels/form')
const {getForm} = require('../typewheels/ourform')
const {StateStore} = require('../typewheels/statestore')
const util = require('util')
const _ = require('lodash')


function getPage(event) {
  if (event.source === 'synthetic') {
    return '1855355231229529'
  }
  if (event.message && event.message.is_echo) {
    return event.sender.id
  }
  else {
    return event.recipient.id
  }
}

function translate(formid) {
  if (+formid > 0) return formid

  const lookup = {
    'LDfNCy': 23,
    'FWtZiz': 374,
    'vpPt5B': 892,
    'nFgfNE': 128,
    'eA5nrh': 457,
    'Ep5wnS': 463,
    'jISElk': 175,
    'vHXzrh': 519,
    'T8fqAk': 144,
    'Kh8nLL': 783,
    'CwU4bp': 637,
    'fzh2vu': 415,
    'Q4NrGz': 901,
  }

  const code = lookup[formid]
  if (!code) throw new Error ('couldnt find code for: ' + formid)
  return code
}


class Responser {
  constructor(chatbase) {
    this.chatbase = chatbase
    this.stateStore = new StateStore(chatbase)
    this.cache = new Cacheman()
    this.getForm = (pageid, shortcode) => this.cache.wrap(`form:${pageid}:${shortcode}`, () => getForm(pageid, shortcode), '360s')
  }

  async updateStore(userId, e) {
    let vals

    const state = await this.stateStore.getState(userId, e)
    const parsedEvent = this.stateStore.parseEvent(e)
    const output = exec(state, parsedEvent)
    const newState = apply(state, output)

    const flowId = newState.forms.length

    // TEMP TRANSITION
    const shortcode = translate(newState.forms.slice(-1)[0])

    const pageid = getPage(parsedEvent)

    const [form, surveyId] = await this.getForm(pageid, shortcode)

    const upd = output && update(output)

    if (upd) {
      const [q, value] = upd
      const timestamp = parsedEvent.timestamp
      const [qidx, {title, ref}] = getField({form}, q, true)
      vals = [surveyId, flowId, userId, ref, qidx, title, value, new Date(timestamp)]
    }

    await this.stateStore.updateState(userId, newState)

    return vals
  }

  async write ({key:userId, value}) {
    try {
      const vals = await this.updateStore(userId, value)
      if (vals) await this.put(vals)
      return null
    }
    catch (error) {
      if (error instanceof FieldError) {
        console.warn(error)
        // Ignore FieldErrors
      } else {
        console.warn(error)
        console.log('ERROR OCCURRED DURING EVENT: ')
        console.log(util.inspect(JSON.parse(value), null, 8))
      }
      return null
    }
  }

  put (vals) {
    const query = `INSERT INTO responses(surveyid, flowid, userid, question_ref, question_idx, question_text, response, timestamp)
		   values($1, $2, $3, $4, $5, $6, $7, $8)
		   ON CONFLICT(userid, timestamp) DO NOTHING`

    return this.chatbase.pool.query(query, vals)
  }

}

module.exports = { Responser, getPage }
