const express = require('express');
const CubejsServerCore = require('@cubejs-backend/server-core');
const cors = require('cors')({ exposedHeaders: ['Content-Disposition'] });
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

CubejsServerCore.create().initApp(app);

module.exports = app;
