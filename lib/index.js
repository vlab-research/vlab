const util = require('util')
const Cacheman = require('cacheman')
const {exec, apply, act} = require('./typewheels/machine')
const {StateStore} = require('./typewheels/statestore')
const {sendMessage, getUserInfo } = require('./messenger')
const {getForm} = require('./typewheels/ourform')
const {BotSpine} = require('@vlab-research/botspine')
const {pipeline} = require('stream')
const {getPage} = require('./responses/responser')


// Cache form from Database
const cache = new Cacheman()
const getFormCached = (pageid, shortcode) => cache.wrap(`form:${pageid}:${shortcode}`, () => getForm(pageid, shortcode), process.env.FORM_CACHED || '60s')
const getUserCached = id => cache.wrap(`user:${id}`, () => getUserInfo(id), process.env.USER_CACHED || '60s')


// Sketch for new Machine class:
// newState, actions = machine.transition(event)
// for (action of actions) {
//   // act
// }
// machine.updateState(newState)

// Does all the work
function processor(stateStore) {
  return async function _processor ({ key:userId, value:event }) {

    try {
      const state = await stateStore.getState(userId, event)
      console.log('STATE: ', state)

      const parsedEvent = stateStore.parseEvent(event)
      const output = exec(state, parsedEvent)
      console.log('OUTPUT: ', output)
      const newState = apply(state, output)

      const shortcode = newState.forms.slice(-1)[0]
      const pageid = getPage(parsedEvent)

      const [form, surveyid] = await getFormCached(pageid, shortcode)
      const user = await getUserCached(userId)

      const actions = act({form, user}, state, output)

      for (action of actions) {

        await sendMessage(userId, action, cache)
        console.log(action)
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


pipeline(spine.source(),
         spine.transform(processor(stateStore)),
         spine.sink(),
         err => console.error(err))
