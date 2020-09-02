const {getField, FieldError} = require('../typewheels/form')
const {StateStore} = require('../typewheels/statestore')
const {Machine} = require('../typewheels/transition')
const {TokenStore} = require('../typewheels/tokenstore')
const util = require('util')

async function responseVals(transition, machine) {
  const { newState, update, form, surveyId:surveyid, pageId, userId:userid, timestamp } = transition

  if (update) {
    const [q, response] = update
    const shortcode = newState.forms.slice(-1)[0]

    const flowid = newState.forms.length
    const [question_idx, {title:question_text, ref:question_ref}] = getField({form}, q, true)

    const {seed, form:parent_shortcode, startTime} = newState.md
    const metadata = newState.md

    const [__, parent_surveyid] = await machine.getForm(pageId, parent_shortcode, startTime)

    return {
      parent_surveyid,
      parent_shortcode,
      surveyid,
      shortcode,
      flowid,
      userid,
      question_ref,
      question_idx,
      question_text,
      response,
      seed,
      metadata,
      timestamp,
      }
  }
}

class Responser {
  constructor(chatbase) {
    this.chatbase = chatbase
    this.stateStore = new StateStore(chatbase)
    this.tokenStore = new TokenStore(chatbase.pool)
    this.machine = new Machine('600s', this.tokenStore)
  }

  async updateStore(userId, e) {
    const state = await this.stateStore.getState(userId, e)
    const t = await this.machine.transition(state, userId, e)
    const vals = responseVals(t, this.machine)
    await this.stateStore.updateState(userId, t.newState)
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
        console.error(error)
        console.log('ERROR OCCURRED DURING EVENT: ')
        console.log(util.inspect(JSON.parse(value), null, 8))
      }
      return null
    }
  }



  put (vals) {
    const query = `INSERT INTO responses(parent_surveyid,
                                         parent_shortcode,
                                         surveyid,
                                         shortcode,
                                         flowid,
                                         userid,
                                         question_ref,
                                         question_idx,
                                         question_text,
                                         response,
                                         seed,
                                         metadata,
                                         timestamp)
		   values($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
		   ON CONFLICT(userid, timestamp, question_ref) DO NOTHING`

    return this.chatbase.pool.query(query, vals)
  }

}

module.exports = { Responser, responseVals }
