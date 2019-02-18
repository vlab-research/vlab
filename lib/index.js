const util = require('util')
const Cacheman = require('cacheman')
const Kafka = require('node-rdkafka')
const {Machine} = require('./typewheels/form')
const {getCurrentForm, getMessage, getState} = require('./typewheels/machine')
const {KeyedStreamer, PromiseStream} = require('./streams')
const {EventStore} = require('./eventstore')
const gcs = require('./chatbase-gcs')
const {sendMessage, getUser, makeFakeEcho } = require('./messenger')
const {getForm} = require('./typewheels/typeform')


// Cache form from Typeform
const cache = new Cacheman()
const getFormCached = form => cache.wrap('form', () => getForm(form), '30s')


// Does all the work
async function processor (message, consumer, eventStore) {
  const user = message.key.toString()
  const event = message.value.toString()

  const events = await eventStore.getEvents(user, event)
  const [formId, log] = getCurrentForm(events.map(JSON.parse))
  const form = await getFormCached(formId)

  const action = getMessage(log, form)

  if (action) {
    await sendMessage(user, action, cache)
    console.log(action)
  }

  consumer.commitMessage(message)
  eventStore.put(user, event)
}



// EventStore with GCS backend
const eventStore = new EventStore(gcs)

// Create stream to handle back pressure
const subStreamer = () => new PromiseStream(m => processor(m,
                                                           stream.consumer,
                                                           eventStore))
const processStream = new KeyedStreamer(m => m.key.toString(),
                                        subStreamer,
                                        {highWaterMark: 200})

// KAFKA
const kafkaOpts = {
  'group.id': 'replybot',
  'metadata.broker.list': `${process.env.KAFKA_BROKER}:${process.env.KAFKA_PORT}`
}
const stream = new Kafka.createReadStream(kafkaOpts, {}, { topics: ['chat-events']})

// Run!
stream
  .pipe(processStream)
  .on('error', err => {
    console.error(err)
  })
