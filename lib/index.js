const util = require('util')
const r2 = require('r2')
const {Machine} = require('./typewheels/transition')
const {StateStore} = require('./typewheels/statestore')
const {sendMessage} = require('./messenger')
const {responseVals} = require('./responses/responser')
const {BotSpine} = require('@vlab-research/botspine')
const {pipeline} = require('stream')
const {TokenStore} = require('./typewheels/tokenstore')
const {producer, producerReady} = require('./producer')

async function publishResults(user, page, response, metadata) {
  const url = process.env.BOTSERVER_URL
  const json = { user,
                 page,
                 event: {type: 'platform_response', value: {metadata, response}}}

  // TODO: secure!
  const headers = {}
  await r2.post(`${url}/synthetic`, { headers, json }).response
}

async function publishState(userid, pageid, updated, state) {
  await producerReady

  const message = { userid, pageid, updated, current_state: state.state, state_json: state }
  const data = Buffer.from(JSON.stringify(message))
  producer.produce(process.env.VLAB_STATE_TOPIC, null, data, userid)
}

async function publishResponses(message) {
  await producerReady
  const data = Buffer.from(JSON.stringify(message))
  producer.produce(process.env.VLAB_RESPONSE_TOPIC, null, data, message.userid)
}


// Does all the work
function processor(machine, stateStore) {
  return async function _processor ({ key:userId, value:event }) {

    try {
      const state = await stateStore.getState(userId, event)
      console.log('STATE: ', state)
      const transition = await machine.transition(state, userId, event)
      const { newState, actions, output, pageId, pageToken } = transition
      console.log('OUTPUT: ', output)

      for (const action of actions) {
        console.log('ACTION: ', action)

        const res = await sendMessage(action, pageToken)
        await publishResults(userId, pageId, res, action.metadata)
      }

      // Update topics for database
      await publishResponses(responseVals(transition, machine))
      await publishState(userId, pageId, transition.timestamp, newState)

      await stateStore.updateState(userId, newState)
    }
    catch (e) {


      // TODO: make user enter state BLOCKED!
      // and add logic to deal with it.
      // usually this means:
      // A message wasn't sent, but may be pending,
      // this means the bot doesn't know what to do
      // and assumes it should wait for the message
      // to be sent, but it never sends.
      // Will need to have some concept of time,
      // otherwise it will never works.

      console.error('Error from ReplyBot: \n',
                    e.message,
                    '\n Error occured during event: ', util.inspect(JSON.parse(event), null, 8))
      console.error(e.stack)
    }
  }
}

// EventStore with chatbase backend
const Chatbase = require(process.env.CHATBASE_BACKEND)
const chatbase = new Chatbase()
const stateStore = new StateStore(chatbase)
const tokenstore = new TokenStore(chatbase.pool)
const machine = new Machine('60m', tokenstore) // SET TTL!


// Create multiple spines for parallelism within container?
const spine = new BotSpine('replybot')
pipeline(spine.source(),
         spine.transform(processor(machine, stateStore)),
         spine.sink(),
         err => console.error(err))
