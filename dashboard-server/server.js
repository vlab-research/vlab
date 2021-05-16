const express = require('express');
const CubejsServerCore = require('@cubejs-backend/server-core');
const cors = require('cors');
const bodyparser = express.json();

const router = require('./api');
const auth = require('./middleware/auth');
const { API_VERSION } = require('./config').SERVER;
const app = express();
const morgan = require('morgan');

app
  .use(morgan('tiny'))
  .use(cors({ exposedHeaders: ['Content-Disposition'] }))
  .use(bodyparser)
  .use(`/api/v${API_VERSION}`, auth, router)
  .use(function(err, req, res, next) {
    if (err.name === 'UnauthorizedError') {
      res.status(401).send('Invalid Token.');
    }
  })
  .use('/health', (req, res) => {
    // TODO: check connection to DB
    return res.status(200).send('OK');
  });

const options = {
  devServer: false,
  checkAuthMiddleware: auth,
};

CubejsServerCore.create(options).initApp(app);

module.exports = app;
