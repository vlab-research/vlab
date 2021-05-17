const {Readable} = require('stream')

class Buffered {
  constructor(fn) {
    this.fn = fn
    this.buff = []
  }

  async next() {
    if (this.buff.length === 0) {
      const res = await this.fn()
      if (!res) return res
      this.buff = res
    }

    return this.buff.shift()
  }
}

// query is a function that takes a limit and
// returns a promise that resolvs to an array
// and a new limit
class DBStream extends Readable {
  constructor(query, init, streamOpts) {
    super({objectMode: true, ...streamOpts})
    this.query = query
    this.lim = init
    this.dat = []

    this.buffer = new Buffered(this._fetch.bind(this))
  }

  async _fetch() {
    const qr = await this.query(this.lim)

    if (!Array.isArray(qr) || qr.length !== 2) {
      throw new Error('Query function from DBStream did not return array of length 2: ', qr)
    }

    const [res, lim] = qr
    if (!res) return null
    this.lim = lim
    return res
  }

  async _go() {
    this.running = true
    while (true) {
      try {
        const res = await this.buffer.next()
        if (!this.push(res)) break
        if (res === null) {
          this.emit('end')
          break
        }
      }
      catch (e) {
        this.emit('error', e)
      }
    }
    this.running = false
  }

  _read() {
    if (!this.running) this._go()
  }
}


async function messagesQuery(pool, lim) {

  const query = `WITH r as (SELECT *, ROW_NUMBER() OVER (ORDER BY timestamp) AS row_number
                 FROM messages ORDER BY timestamp ASC)
                 SELECT * FROM r WHERE row_number > $1 ORDER BY row_number LIMIT 100;`

  const res = await pool.query(query, [lim])
  const final = res.rows.slice(-1)[0]

  if (!final) return [null, null]

  // deal with error for final[column] ?
  return [res.rows, final['row_number']]
}


module.exports = { Buffered, DBStream, messagesQuery }
