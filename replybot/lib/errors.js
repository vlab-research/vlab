class MachineIOError extends Error {
  constructor(tag, msg, details) {
    super(msg)
    this.tag = tag
    this.details = details
  }
  get name() {
    return this.constructor.name;
  }
}

async function iowrap(msg, tag, fn, ...args) {
  try {
    const res = await fn(...args)
    return res
  } catch(e) {
    const err = new MachineIOError(tag, msg, e.details)
    err.stack = e.stack
    throw err
  }
}

module.exports = { MachineIOError, iowrap }
