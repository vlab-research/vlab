const Cacheman = require('cacheman')
const {exec, apply, update} = require('../typewheels/machine')
const {getField, FieldError} = require('../typewheels/form')
const {getForm} = require('../typewheels/typeform')
const {StateStore} = require('../typewheels/statestore')
const util = require('util')
const _ = require('lodash')


class Responser {
  constructor(chatbase) {
    this.chatbase = chatbase
    this.stateStore = new StateStore(chatbase)
    this.cache = new Cacheman()
    this.getForm = form => this.cache.wrap(`form:${form}`, () => getForm(form), '3600s')
  }

  async updateStore(userId, e) {
    let vals

    const state = await this.stateStore.getState(userId, e)
    const parsedEvent = this.stateStore.parseEvent(e)
    const output = exec(state, parsedEvent)
    const newState = apply(state, output)

    const flowId = newState.forms.length
    const formId = newState.forms.slice(-1)[0]

    const form = await this.getForm(formId)
    const upd = output && update(output)

    if (upd) {
      const [q, value] = upd
      const timestamp = parsedEvent.timestamp
      const [qidx, {title, ref}] = getField({form}, q, true)
      vals = [formId, flowId, userId, ref, qidx, title, value, new Date(timestamp)]
    }

    await this.stateStore.updateState(userId, newState)

    return vals
  }

  async write ({key:userId, value}) {

    try {
      const vals = await this.updateStore(userId, value)
      if (vals) await this.put(vals)
    }
    catch (error) {
      if (error instanceof FieldError) {
        // Ignore FieldErrors
      } else {
        console.warn(error)
        console.log('ERROR OCCURRED DURING EVENT: ')
        console.log(util.inspect(JSON.parse(value), null, 8))
      }
    }
  }

  put (vals) {
    const query = `INSERT INTO responses(formid, flowid, userid, question_ref, question_idx, question_text, response, timestamp)
		   values($1, $2, $3, $4, $5, $6, $7, $8)
		   ON CONFLICT(userid, timestamp) DO NOTHING`

    return this.chatbase.pool.query(query, vals)
  }

}

module.exports = { Responser }
