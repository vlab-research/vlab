const util = require('util')
const request = require('request')
const r2 = require('r2')
const {getForm, verifyToken, getUser} = require('./services')
const {Machine} = require('./typewheels/form')
const {getState} = require('./typewheels/typewheels')
const farmhash = require('farmhash')
const Cacheman = require('cacheman')
const Redis = require('ioredis')
const Queue = require('bull')

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


const redis = new Redis(process.env.REDIS_PORT, process.env.REDIS_HOST)
const cache = new Cacheman()

const q = new Queue('chat-events', {
  redis: { sentinels: [{host: process.env.REDIS_HOST }],
           name: 'kiwi-redis-ha' }
})

q.on('error', (err) => {
  console.error(`A queue error happened: ${err.message}. Connecting to: ${process.env.REDIS_HOST} on port ${process.env.REDIS_PORT}`)
})

const getFormCached = form => cache.wrap('form', () => getForm(form), '30s')

q.process(async ({data:event}, done) => {
  try {

    const user = getUser(event)
    await redis.lpush(user, JSON.stringify(event))

    const machine = new Machine()
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

    done()

  } catch (error) {
    console.error('[ERR] processJob: ', error)
    done(error)
  }
})
