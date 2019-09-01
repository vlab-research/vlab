const express = require('express')
const {getUser} = require('./users')
const morgan = require('morgan')
const zmq = require('zeromq')
const sock = zmq.socket('pub');

sock.bindSync("tcp://0.0.0.0:4000");
console.log("Producer bound to port 4000");

const app = express();
app.use(morgan('tiny'))

app.get('/:id', (req, res) => res.send(getUser(req.params.id)));

app.post('/me/messages', express.json(), async (req, res) => {
  const data = Buffer.from(JSON.stringify(req.body))
  sock.send(['messages', data])

  res.send({res: 'response'});
});

app.listen(3000)

module.exports = app;
