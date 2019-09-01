const Koa = require('koa')
const bodyParser = require('koa-bodyparser')
const cors = require('@koa/cors')
const http = require('http')
const Router = require('koa-router')
const Kafka = require('node-rdkafka')
const util = require('util')

function getUser(event) {
  const PAGE_ID = process.env.FB_PAGE_ID

  if (event.sender.id === PAGE_ID) {
    return event.recipient.id
  }
  else if (event.recipient.id === PAGE_ID){
    return event.sender.id
  }
  else {
    throw new Error('Non Existent User!')
  }
}

const EVENT_TOPIC = process.env.BOTSERVER_EVENT_TOPIC

const producer = new Kafka.Producer({
  'metadata.broker.list': process.env.KAFKA_BROKERS,
  'retry.backoff.ms': 200,
  'message.send.max.retries': 10,
  'socket.keepalive.enable': true,
  'queue.buffering.max.messages': 100000,
  'queue.buffering.max.ms': 1000,
  'batch.num.messages': 1000000
}, {}, {
  topic: EVENT_TOPIC
});

producer.connect()

producer.on('event.error', err => {
  console.error('Error from producer');
  console.error(err);
})

const producerReady = new Promise((resolve, reject) => {

  const timeout = setTimeout(() => {
    reject(new Error('Unable to connect to kafka producer'))
  }, process.env.KAFKA_CONNECTION_TIMEOUT || 30000)


  producer.on('ready', () => {
    console.log('producer ready')
    clearTimeout(timeout)
    resolve()
  })

}).catch(err => {
  setTimeout(() => { throw err })
})


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

  for (entry of ctx.request.body.entry) {
    try {
      console.log(util.inspect(entry, null, 8))

      // abstraction layer??
      const message = {...entry.messaging[0], source: 'messenger'}
      const user = getUser(message)
      const data = Buffer.from(JSON.stringify(message))

      producer.produce(EVENT_TOPIC, null, data, user)
    } catch (error) {
      console.error('[ERR] handleEvents: ', error)
    }
  }
  ctx.status = 200
}


// TODO: move into another service?
const handleSyntheticEvents = async (ctx) => {
  await producerReady

  try {
    const {body} = ctx.request

    const message = {...body, source: 'synthetic', timestamp: Date.now()}
    const data = Buffer.from(JSON.stringify(message))

    if (!message.user) {
      console.log(body)
      throw new Error('No user!')
    }

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

const app = new Koa()
app
  .use(bodyParser())
  .use(cors())
  .use(router.routes())
  .use(router.allowedMethods())

http.createServer(app.callback()).listen(process.env.PORT || 8080)
