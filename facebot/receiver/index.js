const express = require('express')
const {getUser} = require('./users')
const util = require('util')
const shortid = require('shortid');

const app = express()

const err = {error: {message: 'Facebot has no answer to give.', code: 99999 }}

const messages = {}
const callbacks = {}

app.get('/:id', (req, res) => res.send(getUser(req.params.id)))

app.post('/me/messages', express.json(), async (req, res) => {
  const data = req.body
  let sent;

  const cb = (response) => {
    if (sent) return
    res.json(response)
    sent = true
  }

  setTimeout(() => {
    if (sent) return
    console.error('Timed out in response to: ', util.inspect(data, null, 6))
    res.json(err)
    sent = true
  }, 10000)

  if (!data.recipient) {
    console.error('NO RECIPIENT: ')
    console.error(data)
    res.json(err)
  }

  const rec = data.recipient.id || data.recipient.one_time_notif_token

  if (!messages[rec]) {
    messages[rec] = [[data, cb]]
  } else {
    messages[rec].push([data, cb])
  }
});

app.get('/sent/:id', express.json(), async (req, res) => {
  const rec = req.params.id

  const msgs = messages[rec]
  if (!msgs || msgs.length == 0) {
    return res.json({ missing: true })
  }

  const [data, cb] = msgs.shift()
  const token = shortid.generate()
  callbacks[token] = cb

  const json = { data, token }
  res.json(json)
});

app.post('/respond/:token', express.json(), async (req, res) => {
  const token = req.params.token
  const cb = callbacks[token]
  cb(req.body)
  res.send('OK')
});

app.listen(3000)

module.exports = app
