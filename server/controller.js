const fs = require('fs')
const util = require('util')
const request = require('request')
const r2 = require('r2')
const {getForm, verifyToken, getUser} = require('./services')
const {Machine} = require('./typewheels/form')
const {getState} = require('./typewheels/typewheels')
const farmhash = require('farmhash')

async function sendMessage(recipientId, response, redis) {

  // quick hack to avoid double sending!
  const i = farmhash.hash32(JSON.stringify(response))
  if (await redis.exists(`sent:${i}`)) return
  await redis.set(`sent:${i}`, true, 'EX', 2)

  request({
    url: 'https://graph.facebook.com/v3.2/me/messages',
    headers: { Authorization: `Bearer ${process.env.PAGE_ACCESS_TOKEN}`},
    method: 'POST',
    json: {
      recipient: { id: recipientId },
      message: response,
    }
  }, function (error, response, body) {
    if (error) {
      console.log('Error sending message: ', error);
    } else if (response.body.error) {
      console.log('Error: ', response.body.error);
    }
  })
}

var Redis = require('ioredis')
var redis = new Redis(process.env.REDIS_PORT, process.env.REDIS_HOST)

var Cacheman = require('cacheman')
var cache = new Cacheman()
const getFormCached = form => cache.wrap('form', () => getForm(form), '30s')

const startSurvey = async (ctx) => {
  console.log('>>>>>>>>> REQUEST <<<<<<<<<<<<<<<<<')
  for (entry of ctx.request.body.entry) {
    try {
      console.log('+++ ENTRY: ', entry)

      // TODO: change to use Redis as queue
      // and move sending to another service that does queue processing!
      // thus we remove race conditions

      const event = entry.messaging[0]
      const user = getUser(event)
      const machine = new Machine()

      await redis.lpush(user, JSON.stringify(event))
      const r = await redis.lrange(user, 0, -1)
      r.reverse()
      const log = r.map(JSON.parse)
      const state = getState(log)

      if (!state) throw new Error('User does not have any current form!')

      const form = await getFormCached(state.form)
      const action = machine.exec(state, form, log)

      if (action) {
        await sendMessage(user, action, redis)
      }
    } catch (error) {
      console.error('[ERR] startSurvey: ', error)
    }
  }
  ctx.status = 200
}

module.exports = {
  verifyToken,
  startSurvey
}
