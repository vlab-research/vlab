const Koa = require('koa')
const bodyParser = require('koa-bodyparser')
const http = require('http')
const Router = require('koa-router')
const Queue = require('bee-queue')

const q = new Queue('chat-events', {
  redis: { host: process.env.REDIS_HOST, port: process.env.REDIS_PORT },
  isWorker: false
})

q.on('error', (err) => {
  console.error(`A queue error happened: ${err.message}`)
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

const handleEvents = async (ctx) => {
  console.log('>>>>>>>>>>>>> REQUEST <<<<<<<<<<<<<<<<<')

  await q.ready()

  for (entry of ctx.request.body.entry) {
    try {
      console.log('+++ ENTRY: ', entry)
      const event = entry.messaging[0]
      const job = q.createJob(event)
      const res = await job.retries(3).save()

    } catch (error) {
      console.error('[ERR] handleEvents: ', error)
    }
  }
  ctx.status = 200
}

const router = new Router()
router.get('/webhooks', verifyToken)
router.post('/webhooks', handleEvents)

const app = new Koa()
app
  .use(bodyParser())
  .use(router.routes())
  .use(router.allowedMethods())

http.createServer(app.callback()).listen(process.env.PORT)
