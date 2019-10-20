const util = require('util')
const {Machine} = require('./typewheels/transition')
const {StateStore} = require('./typewheels/statestore')
const {sendMessage } = require('./messenger')
const {BotSpine} = require('@vlab-research/botspine')
const {pipeline} = require('stream')

// Does all the work
function processor(machine, stateStore) {
  return async function _processor ({ key:userId, value:event }) {

    try {
      const state = await stateStore.getState(userId, event)
      console.log('STATE: ', state)
      const { newState, actions, output } = await machine.transition(state, userId, event)
      console.log('OUTPUT: ', output)

      for (action of actions) {

        console.log('ACTION: ', action)
        await sendMessage(userId, action)
      }

      await stateStore.updateState(userId, newState)
    }

    catch (e) {
      console.error('Error from ReplyBot: ', e.message)
      console.error(e.stack)
    }
  }
}

// EventStore with chatbase backend
const Chatbase = require(process.env.CHATBASE_BACKEND)
const stateStore = new StateStore(new Chatbase())
const spine = new BotSpine('replybot')
const machine = new Machine('120s') // SET TTL!

pipeline(spine.source(),
         spine.transform(processor(machine, stateStore)),
         spine.sink(),
         err => console.error(err))
