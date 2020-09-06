const r2 = require('r2')
const sender = require('./sender')
const util = require('util')
const {makeEcho} = require('@vlab-research/mox')
const {snooze} = require('./utils')

const facebot = 'http://gbv-facebot'

async function receive(id) {
  while (true) {
    const res = await r2.get(`${facebot}/sent/${id}`).json;
    if (res.data) {
      return res
    }
    await snooze(50)
  }
}

async function send(token, json) {
  const res = await r2.post(`${facebot}/respond/${token}`, {json}).response;
  return res
}

async function flowMaster(userId, testFlow) {
  for (const [res, get, gives, ...xtras] of testFlow) {
    let sent

    if (xtras.length) {
      const [recip] = xtras
      sent = await receive(recip)
    } else {
      sent = await receive(userId)
    }

    const {data, token} = sent

    const msg = data.message

    try {
      msg.should.eql(get)
      await send(token, res)
    }
    catch (e) {
      console.log(util.inspect(msg, null, 8))
      console.log(util.inspect(get, null, 8))
      console.error(e)
      const r = { error: { message: 'test broke', code: 99999 }}
      await send(token, r)
      throw e
    }

    if (!res.error) {
      await sender(makeEcho(get, userId))
    }

    for (let giv of gives) {
      await sender(giv)
    }
  }
}

module.exports = { flowMaster }
