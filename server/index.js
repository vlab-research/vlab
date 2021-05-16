const Koa = require('koa')
const bodyParser = require('koa-bodyparser')
const cors = require('@koa/cors')
const http = require('http')
const Router = require('koa-router')
const util = require('util')
const {getUserFromEvent} = require('@vlab-research/utils')

const {producer, producerReady} = require('./producer')

const EVENT_TOPIC = process.env.BOTSERVER_EVENT_TOPIC

const verifyToken = ctx => {
  if (ctx.query['hub.verify_token'] === process.env.VERIFY_TOKEN) {
    ctx.body = ctx.query['hub.challenge']
    ctx.status = 200
  } else {
    ctx.body = 'invalid verify token'
    ctx.status = 401
  }
}

// TODO: Add validation with APP SECRET!!!
const handleMessengerEvents = async (ctx) => {
  await producerReady

  for (const entry of ctx.request.body.entry) {
    try {
      console.log(util.inspect(entry, null, 8))

      // abstraction layer??
      const message = {...entry.messaging[0], source: 'messenger'}

      // add getPageFromEvent(message)
      const user = getUserFromEvent(message)
      const data = Buffer.from(JSON.stringify(message))

      producer.produce(EVENT_TOPIC, null, data, user)
    } catch (error) {
      console.error('[ERR] handleEvents: ', error)
    }
  }
  ctx.status = 200
}


// TODO: move into another service?
// TODO: secure!
const handleSyntheticEvents = async (ctx) => {
  await producerReady

  try {
    const {body} = ctx.request
    console.log(util.inspect(body, null, 8))


    // TODO: timestamp is all over the place right now.
    // FB sends a timestamp, then Botserver makes the timestamp for synthetic
    // events. So far, so good.
    // However then Scribble takes the kafka timestamp, which
    // is good because then it's replied in the same order its recieved

    // but then what should report.timestamp have?

    const message = {...body, source: 'synthetic', timestamp: Date.now()}
    const data = Buffer.from(JSON.stringify(message))

    if (!message.user) {
      console.log(body)
      throw new Error('No user!')
    }

    // message.page

    producer.produce(EVENT_TOPIC, null, data, message.user)
    ctx.status = 200
  } catch (error) {
    console.error(error)
    ctx.status = 500
  }
}

const router = new Router()
router.get('/webhooks', verifyToken)
router.post('/webhooks', handleMessengerEvents)
router.post('/synthetic', handleSyntheticEvents)
router.get('/health', async ctx => {
  await producerReady
  ctx.status = 200
})

const app = new Koa()
app
  .use(bodyParser())
  .use(cors())
  .use(router.routes())
  .use(router.allowedMethods())

http.createServer(app.callback()).listen(process.env.PORT || 8080)
