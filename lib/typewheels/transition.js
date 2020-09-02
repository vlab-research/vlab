const {exec, apply, act, update} = require('./machine')
const {getForm} = require('./ourform')
const {getUserInfo } = require('../messenger')
const {parseEvent, getPageFromEvent} = require('@vlab-research/utils')
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

  async transition(state, userId, event) {

    // SYNC
    // If throws, should be looked at, will be
    // an edge case, will be deterministic,
    // no point in redoing.
    // It's a kind of BLOCKED...
    // ERROR state? 
    const parsedEvent = parseEvent(event)
    const timestamp = parsedEvent.timestamp
    const output = exec(state, parsedEvent)

    const upd = output && update(output)
    const newState = apply(state, output)

    const shortcode = newState.forms.slice(-1)[0]
    const pageId = getPageFromEvent(parsedEvent)
    const {startTime} = newState.md

    // IO
    // If throws, should probably retry later
    // maybe not deterministic. 
    // BLOCKED? ERROR?
    // could be something like trying to move to a form that doesn't exist
    // or could be facebook user error
    // or could be dashboard api down/overloaded
    // or could be database issue
    // ...
    const pageToken = await this.getPageToken(pageId)
    const [form, surveyId] = await this.getForm(pageId, shortcode, startTime)
    const user = await this.getUser(userId, pageToken)

    // Actions lead to more IO
    // if throws, depends on error,
    // BLOCKED is a good place
    const actions = act({form, user}, state, output)

    return { newState, actions, output, update:upd, form, surveyId, user, pageId, parsedEvent, pageToken, timestamp, userId }
  }
}

module.exports = { Machine }
