const util = require('util')
const r2 = require('r2')
const {Machine} = require('./typewheels/transition')
const {StateStore} = require('./typewheels/statestore')
const {BotSpine} = require('@vlab-research/botspine')
const {pipeline} = require('stream')
const {TokenStore} = require('./typewheels/tokenstore')
const {producer, producerReady} = require('./producer')


async function publishReport(report) {
  const url = process.env.BOTSERVER_URL
  const json = { user: report.user,
                 page: report.page,
                 event: {type: 'machine_report', value: report }}

  // TODO: secure!!
  const headers = {}
  return r2.post(`${url}/synthetic`, { headers, json }).response
}

async function publishState(userid, pageid, updated, state) {
  await producerReady

  const message = { userid, pageid, updated, current_state: state.state, state_json: state }
  const data = Buffer.from(JSON.stringify(message))
  producer.produce(process.env.VLAB_STATE_TOPIC, null, data, userid)
}

async function publishResponses(message) {
  if (!message) return
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

      const report = await machine.run(state, userId, event)
      if (!report) return
      

      console.log('ACTIONS: ', report.actions)
      await publishReport(report)

      if (report.responses) {
        await publishResponses(report.responses)
      }
      if (report.newState) {
        await publishState(report.user, report.page, report.timestamp, report.newState)
        await stateStore.updateState(userId, report.newState)
      }
    }
    catch (e) {

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


// TODO: handle kafka errors (throw them to force restart!)
// Create multiple spines for parallelism within container?
const spine = new BotSpine('replybot')
pipeline(spine.source(),
         spine.transform(processor(machine, stateStore)),
         spine.sink(),
         err => console.error(err))
