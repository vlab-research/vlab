function _resolve(li, e) {
  if (!li) return [e]

  const i = li.indexOf(e)
  return i === -1 ? [...li, e] : li.slice(0,i+1)

}

class EventStore {
  constructor(db) {
    this.db = db
    this.cache = {}
  }

  put (user, event) {
    // Only puts locally!
    // This is intentional, it is
    // currently only used for putting
    // fake echos

    this.cache[user].push(event)
    return this.cache[user]
  }

  async getEvents(user, event) {
    if (this.cache[user]) {
      return this.put(user, event)
    }

    const res = await this.db.get(user)
    const events = _resolve(res, event)
    this.cache[user] = events

    return this.cache[user]
  }

}

module.exports = { _resolve, EventStore }
