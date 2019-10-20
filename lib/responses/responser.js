const {getField, FieldError} = require('../typewheels/form')
const {StateStore} = require('../typewheels/statestore')
const {Machine} = require('../typewheels/transition')
const util = require('util')
const _ = require('lodash')


class Responser {
  constructor(chatbase) {
    this.chatbase = chatbase
    this.stateStore = new StateStore(chatbase)
    this.machine = new Machine('600s')
  }

  async updateStore(userId, e) {
    let vals
    const state = await this.stateStore.getState(userId, e)
    const { newState, update, form, surveyId } =
          await this.machine.transition(state, userId, e)

    if (update) {
      const [q, value] = update
      const flowId = newState.forms.length
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
