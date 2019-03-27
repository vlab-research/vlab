const express = require('express');
const cors = require('cors')();
const bodyparser = express.json();

const router = require('./api');
const auth = require('./middleware/auth');

const app = express();

app
  .use(cors)
  .use(auth)
  .use(bodyparser)
  .use(router);

module.exports = app;
