const express = require('express')
const {getUser} = require('./users')
const morgan = require('morgan')
const Kafka = require('node-rdkafka')

const EVENT_TOPIC = 'facebot'
const producer = new Kafka.Producer(
  {'metadata.broker.list': process.env.KAFKA_BROKERS },
  {},
  { topic: EVENT_TOPIC });

producer.connect()

const producerReady = new Promise((resolve, reject) => {

  const timeout = setTimeout(() => {
    reject(new Error('Unable to connect to kafka producer'))
  }, process.env.KAFKA_CONNECTION_TIMEOUT || 30000)

  producer.on('ready', () => {
    console.log('producer ready')
    clearTimeout(timeout)
    resolve()
  })

}).catch(err => {
  setTimeout(() => { throw err })
})

producer.on('event.error', err => {
  console.error('Error from producer');
  console.error(err);
})

const app = express();
app.use(morgan('tiny'))

app.get('/:id', (req, res) => res.send(getUser(req.params.id)));

app.post('/me/messages', express.json(), async (req, res) => {
  await producerReady
  const data = Buffer.from(JSON.stringify(req.body))
  producer.produce(EVENT_TOPIC, null, data)

  res.send({res: 'response'});
});

app.listen(3000)

module.exports = app;
