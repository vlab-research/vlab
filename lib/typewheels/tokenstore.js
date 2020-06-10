const Cacheman = require('cacheman')

class TokenStore {
  constructor(db, ttl = '24h') {
    if (!db) throw new TypeError('TokenStore must be given a db')

    this.db = db
    this.cache = new Cacheman({ttl})
  }

  _makeKey(page) {
    return `token:${page}`
  }

  async _getToken(page) {
    // use db to get token for page
    const query = `SELECT token FROM facebook_pages WHERE pageid = $1`
  }

  async get(page) {
    const key = this._makeKey(page)
    const cached = await this.cache.get(key)

    if (cached) return cached

    return this._getToken(page)
  }
}

module.exports = { TokenStore }
