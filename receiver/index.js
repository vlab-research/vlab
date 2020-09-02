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
  let sent;
  
  setTimeout(() => {
    if (sent) return
    res.json({error: {message: 'Facebot has no answer to give.', code: 99999 }})
    sent = true
  }, 15000)

  sock.once('message', (message) => {
    if (sent) return
    const response = JSON.parse(message.toString())
    res.send(response)
    sent = true
  })

  const data = JSON.stringify(req.body)
  sock.send(data)
});

app.listen(3000)

module.exports = app
