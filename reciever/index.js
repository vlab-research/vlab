const express = require('express')
const {getUser} = require('./users')
const morgan = require('morgan')
const zmq  = require('zeromq')
const sock = zmq.socket('req')
const util = require('util')


sock.connect('tcp://gbv-facebroker:4000');


const app = express()
app.use(morgan('tiny'))

app.get('/:id', (req, res) => res.send(getUser(req.params.id)))


app.post('/me/messages', express.json(), async (req, res) => {
  req.setTimeout(5000)

  sock.once('message', (message) => {
    const response = JSON.parse(message.toString())
    res.send(response)
  })

  const data = JSON.stringify(req.body)
  sock.send(data)
});

app.listen(3000)

module.exports = app
