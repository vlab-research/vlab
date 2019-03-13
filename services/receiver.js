const express = require('express');
const app = express();
const mocks = require('../test/mocks');

app.get('/:id', (_, res) => res.send(mocks.user));

app.post('/me/messages', express.json(), (req, res) => {
  app.emit('message', req.body);
  res.send('response');
});

module.exports = app;
