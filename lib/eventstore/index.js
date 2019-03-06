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

    if (!this.cache[user]) {
      this.cache[user] = []
    }
    this.cache[user].push(event)
  }


  async getEvents(user, event) {
    let res;

    if (this.cache[user]) {
      res = this.cache[user]
    } else {
      res = await this.db.get(user)
      this.cache[user] = res
    }

    const events = _resolve(res, event)
    return events.map(JSON.parse).map(e => e.messaging[0])
  }

}

module.exports = { _resolve, EventStore }
