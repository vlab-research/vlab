const Koa = require('Koa');
const cors = require('@koa/cors')();
const bodyparser = require('koa-bodyparser')();

const router = require('./api');
const auth = require('./middleware/auth');

const app = new Koa();

app
  .use(cors)
  .use(auth)
  .use(bodyparser)
  .use(router.routes())
  .use(router.allowedMethods());

module.exports = app;
