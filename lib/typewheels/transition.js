const {exec, apply, act, update} = require('./machine')
const {getForm} = require('./ourform')
const {getUserInfo, sendMessage} = require('../messenger')
const {responseVals} = require('../responses/responser')
const {parseEvent, getPageFromEvent} = require('@vlab-research/utils')
const {MachineIOError, iowrap} = require('../errors')
const util = require('util')
const Cacheman = require('cacheman')


class Machine {
  constructor(ttl, tokenStore) {
    const cache = new Cacheman()
    this.cache = cache

    // add timestamp
    this.getForm = (pageid, shortcode, timestamp) => {
      return cache.wrap(`form:${pageid}:${shortcode}:${timestamp}`, () => getForm(pageid, shortcode, timestamp), ttl)
    }
    this.getUser = (id, pageToken) => {
      return cache.wrap(`user:${id}`, () => getUserInfo(id, pageToken), ttl)
    }

    this.getPageToken = page => {
      return cache.wrap(`pagetoken:${page}`, () => tokenStore.get(page), ttl)
    }
  }

  async transition(state, event) {
    const parsedEvent = parseEvent(event)
    const page = getPageFromEvent(parsedEvent)

    const output = exec(state, parsedEvent)
    const newState = apply(state, output)
    return {newState, output, page}
  }

  async actionsResponses(state, userId, event, pageId, newState, output) {
    const parsedEvent = parseEvent(event)
    const timestamp = parsedEvent.timestamp
    const upd = output && update(output)
    const shortcode = newState.forms.slice(-1)[0]

    if (!newState.md) {
      throw new Error(`User without metadata: ${userId}. State: ${util.inspect(newState, null, 8)}`)
    }
    const {startTime} = newState.md


    const pageToken = await iowrap('getPageToken', 'INTERNAL', this.getPageToken, pageId)
    const [form, surveyId] = await iowrap('getForm', 'INTERNAL', this.getForm, 
                                          pageId, shortcode, startTime)


    // iowraps at lower level
    const user = await this.getUser(userId, pageToken)

    // Actions lead to more IO
    // if throws, depends on error,
    // BLOCKED is a good place
    const actions = act({form, user}, state, output)
    const responses = responseVals(newState, upd, form, surveyId, pageId, userId, timestamp)

    return { actions, responses, pageToken }
  }

  async act(actions, pageToken) {

    // iowraps at lower level, will stop at first error
    for (const action of actions) {
      await sendMessage(action, pageToken)
    }
  }


  async run(state, user, event) {
    let newState, output, page

    // SYNC machine error, usually bad event
    try {
      const t = this.transition(state, event)
      newState = t.newState
      output = t.output
      page = t.page

    } catch (e) {
      return { user, page, error: { tag: 'STATE_TRANSITION', message: e.message, state, event }}
    }
    try {

      // Create successful report
      const {actions, pageToken, responses} = await this.actionsResponses(state, user, event, page, newState, output)
      await this.act(actions, pageToken)
      return {user, page, actions, responses, newState}

    } catch (e) {
      if (e instanceof MachineIOError) {
        return {user, page, newState, error: { tag: e.tag, message: e.message, ...e.details }}
      } else {
        return {user, page, newState, error: { tag: 'STATE_ACTIONS', message: e.message }}
      }
    }        
  }
}

module.exports = { Machine }
