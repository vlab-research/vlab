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

    this.sendMessage = sendMessage
  }

  transition(state, event) {
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

    const user = await this.getUser(userId, pageToken)

    const actions = act({form, user}, state, output)
    const responses = responseVals(newState, upd, form, surveyId, pageId, userId, timestamp)

    return { actions, responses, pageToken, timestamp }
  }

  async act(actions, pageToken) {

    for (const action of actions) {
      await this.sendMessage(action, pageToken)
    }
  }


  async run(state, user, event) {
    let newState, output, page, pe, timestamp

    // TODO: don't parse event a million times
    // TODO: TEST!!!!!!!!!!!!! -- something funny with parsedEvent
    try {
      pe = parseEvent(event)
      timestamp = pe.timestamp
    } catch (e) {
      return { timestamp: Date.now(), user, error: { tag: 'CORRUPTED_MESSAGE', message: e.message, stack: e.stack, event }}
    }

    // SYNC machine error, usually bad event
    try {
      const t = this.transition(state, event)
      newState = t.newState
      output = t.output
      page = t.page

      if (output.action === 'NONE') return

    } catch (e) {
      return { timestamp, user, page, error: { tag: 'STATE_TRANSITION', message: e.message, stack: e.stack, state, event }}
    }
    try {

      // Create successful report
      const {actions, pageToken, responses} = await this.actionsResponses(state, user, event, page, newState, output)
      await this.act(actions, pageToken)
      return {timestamp, user, page, actions, responses, newState}

    } catch (e) {
      if (e instanceof MachineIOError) {
        return {timestamp, user, page, newState, error: { ...e.details, tag: e.tag, message: e.message, stack: e.stack }}
      } else {
        return {timestamp, user, page, newState, error: { tag: 'STATE_ACTIONS', message: e.message, stack: e.stack }}
      }
    }
  }
}

module.exports = { Machine }
