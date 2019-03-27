const express = require('express');
const cors = require('cors')();
const bodyparser = express.json();

const router = require('./api');
const auth = require('./middleware/auth');
const { API_VERSION } = require('./config').SERVER;

const app = express();

app
  .use(cors)
  .use(auth)
  .use(bodyparser)
  .use(`/api/v${API_VERSION}`, router);

module.exports = app;
