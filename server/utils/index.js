const stream = require('stream')

class PromiseStream extends stream.Writable {
  constructor (fn, opts) {
    super({ objectMode: true, ...opts})
    this.fn = fn
  }
  write (d, e, c) {
    this.fn(d)
      .then(_ => c(null))
      .catch(c)
  }
}

class KeyedStreamer extends stream.Writable {
  constructor (getKey, makeSubStream, streamOpts) {

    super({ objectMode: true,
            ...streamOpts })

    this.makeSubStream = makeSubStream
    this.getKey = getKey
    this.streams = {}
  }

  write (message, enc, cb) {
    const key = this.getkey(message)

    this.streams[key] = this.streams[key] ||
      this.makeSubstream().on('error', e => this.emit('error', e))

    const s = this.streams[key]
    s.write(message) ? cb(null) : s.once('drain', cb)
  }
}

module.exports = { KeyedStreamer, PromiseStream }
