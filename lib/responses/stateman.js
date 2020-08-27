const util = require('util')
const _ = require('lodash')
const {pipeline} = require('stream')
const {BotSpine} = require('@vlab-research/botspine')
const {Machine} = require('../typewheels/transition')
const {StateStore} = require('../typewheels/statestore')
const {TokenStore} = require('../typewheels/tokenstore')
const Chatbase = require(process.env.CHATBASE_BACKEND)

class Stateman {
  constructor(chatbase) {
    this.chatbase = chatbase
    this.stateStore = new StateStore(chatbase)
    this.tokenStore = new TokenStore(chatbase.pool)
    this.machine = new Machine('600s', this.tokenStore)
  }

  async write ({key:userId, value}) {
    try {
      const vals = await this.updateStore(userId, value)
      if (vals) await this.put(vals)
      return null
    }
    catch (error) {
      console.error(error)
      console.log('ERROR OCCURRED DURING EVENT: ')
      console.log(util.inspect(JSON.parse(value), null, 8))
      return null
    }
  }

  async updateStore(userId, e) {
    const state = await this.stateStore.getState(userId, e)
    const { newState, parsedEvent, pageId } =
          await this.machine.transition(state, userId, e)

    if (_.isEqual(state, newState)) return null

    const timestamp = new Date(parsedEvent.timestamp)
    return [userId, pageId, timestamp, newState.state, newState]
  }

  async put (vals) {
    const query = `UPSERT INTO states(userid,
                                      pageid,
                                      updated,
                                      current_state,
                                      state_json)
                   VALUES ($1, $2, $3, $4, $5)`

    return this.chatbase.pool.query(query, vals)
  }
}


const chatbase = new Chatbase()
for (let i = 0; i < 24; i++) {
  const spine = new BotSpine('stateman')
  const stateman = new Stateman(chatbase)

  pipeline(spine.source(),
           spine.transform(stateman.write.bind(stateman)),
           spine.sink(),
           err => console.error(err))
}
