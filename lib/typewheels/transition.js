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
    const parsedEvent = parseEvent(event)
    const output = exec(state, parsedEvent)

    const upd = output && update(output)

    const newState = apply(state, output)

    const shortcode = newState.forms.slice(-1)[0]
    const pageId = getPageFromEvent(parsedEvent)
    const pageToken = await this.getPageToken(pageId)

    const {startTime} = newState.md

    const [form, surveyId] = await this.getForm(pageId, shortcode, startTime)
    const user = await this.getUser(userId, pageToken)

    const actions = act({form, user}, state, output)

    return { newState, actions, output, update:upd, form, surveyId, user, pageId, parsedEvent, pageToken }
  }
}

module.exports = { Machine }
