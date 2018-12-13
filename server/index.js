var fs = require('fs')
const Koa = require('koa')
const https = require('https')
const bodyParser = require('koa-bodyparser')

const router = require('./router')
// const saveForm = require('./functions/typeform-getter')

const app = new Koa()

app
  .use(bodyParser())
  .use(router.routes())
  .use(router.allowedMethods())

https.createServer(app.callback()).listen(process.env.PORT)
