const {exec, apply, act, update} = require('./machine')
const {getForm} = require('./ourform')
const {getUserInfo } = require('../messenger')
const {parseEvent} = require('@vlab-research/utils')
const Cacheman = require('cacheman')

function getPage(event) {
  if (event.source === 'synthetic') {
    return '1855355231229529' // TODO --> WTF???
  }
  if (event.message && event.message.is_echo) {
    return event.sender.id
  }
  else {
    return event.recipient.id
  }
}

class Machine {
  constructor(ttl) {
    const cache = new Cacheman()
    this.getForm = (pageid, shortcode) => {
      return cache.wrap(`form:${pageid}:${shortcode}`, () => getForm(pageid, shortcode), ttl)
    }
    this.getUser = id => {
      return cache.wrap(`user:${id}`, () => getUserInfo(id), ttl)
    }
  }

  async transition(state, userId, event) {
    const parsedEvent = parseEvent(event)
    const output = exec(state, parsedEvent)

    const upd = output && update(output)

    const newState = apply(state, output)
    const shortcode = newState.forms.slice(-1)[0]
    const pageId = getPage(parsedEvent)

    const [form, surveyId] = await this.getForm(pageId, shortcode)
    const user = await this.getUser(userId)

    const actions = act({form, user}, state, output)

    return { newState, actions, output, update:upd, form, surveyId, user }
  }
}

module.exports = { Machine }
