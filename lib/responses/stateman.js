const _ = require('lodash')
const {pipeline} = require('stream')
const {BotSpine} = require('@vlab-research/botspine')
const {Machine} = require('../typewheels/transition')
const {StateStore} = require('../typewheels/statestore')
const Chatbase = require(process.env.CHATBASE_BACKEND)

const chatbase = new Chatbase()
const stateStore = new StateStore(chatbase)
const machine = new Machine('600s')
const spine = new BotSpine('stateman')

console.log('STATEMAN: connected')

async function writeState (pool, {key:userId, value:e}) {

  try {
    const state = await stateStore.getState(userId, e)
    const { newState, parsedEvent } =
          await machine.transition(state, userId, e)

    const timestamp = new Date(parsedEvent.timestamp)

    if (!_.isEqual(state, newState)) {
      const vals = [userId, timestamp, newState]
      await pool.query(`UPSERT INTO states(userid, "timestamp", state) VALUES ($1, $2, $3)`,
                       vals)
    }
  } catch (e) {
    console.error(e)
  }

}

pipeline(spine.source(),
         spine.transform(writeState.bind(null, chatbase.pool)),
         spine.sink(),
         err => console.error(err))
