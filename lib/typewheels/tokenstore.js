class TokenStore {
  constructor(db) {
    if (!db) throw new TypeError('TokenStore must be given a db')

    this.db = db
  }

  async _getToken(page) {
    // TODO: move to separate lib and test...
    const query = `SELECT token FROM facebook_pages WHERE pageid = $1`
    const res = await this.db.query(query, [page])

    if (res.rows.length === 0) {
      throw new Error(`Cannot find token for facebook page with id: ${page}`)
    }
    
    const {token} = res.rows[0]
    return token
  }

  async get(page) {
    return this._getToken(page)
  }
}

module.exports = { TokenStore }
