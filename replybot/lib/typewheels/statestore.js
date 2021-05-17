const Cacheman = require('cacheman')
const {getState} = require('./machine')
const {parseEvent} = require('@vlab-research/utils')

function _resolve(li, e) {
  if (!e) return li
  if (!li) return [e]

  const i = li.indexOf(e)
  return i === -1 ? [...li, e] : li.slice(0,i+1)
}


class StateStore {
  constructor(db, ttl = '24h') {
    if (!db) throw new TypeError('StateStore must be given a db')

    this.db = db
    this.cache = new Cacheman({ttl})
  }

  _makeKey(user) {
    return `state:${user}`
  }

  parseEvent(event) {
    return parseEvent(event)
  }

  async _getEvents(user, event) {
    const res = await this.db.get(user)
    return _resolve(res, event)
      .map(this.parseEvent)
      .slice(0,-1)
  }

  // get state UP TO BUT NOT INCLUDING this event
  async getState(user, event) {
    const key = this._makeKey(user)
    const cached = await this.cache.get(key)

    if (cached) return cached

    const events = await this._getEvents(user, event)
    return getState(events)
  }

  async updateState(user, state) {
    const key = this._makeKey(user)
    return this.cache.set(key, state)
  }
}

module.exports = { _resolve, StateStore }
