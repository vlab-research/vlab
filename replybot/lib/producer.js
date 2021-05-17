const Kafka = require('node-rdkafka')

const producer = new Kafka.Producer({
  'metadata.broker.list': process.env.KAFKA_BROKERS,
  'retry.backoff.ms': 200,
  'message.send.max.retries': 10,
  'socket.keepalive.enable': true,
  'queue.buffering.max.messages': 100000,
  'queue.buffering.max.ms': 1000,
  'batch.num.messages': 1000000
}, {}, {});

producer.connect()
producer.setPollInterval(1000)

producer.on('event.error', err => {
  console.error('Error from producer');
  throw err;
})

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

module.exports = {producer, producerReady}
