const util = require('util')
const Cacheman = require('cacheman')
const Kafka = require('node-rdkafka')
const {Machine} = require('./typewheels/form')
const {getState} = require('./typewheels/typewheels')
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
  const log = events.map(JSON.parse)
  const state = getState(log)
  const form = await getFormCached(state.form)
  const machine = new Machine()
  const action = machine.exec(state, form, log)

  if (action) {
    await sendMessage(user, action, cache)
    eventStore.put(user, makeFakeEcho(user, action))
    console.log(action)
  }

  consumer.commitMessage(message)
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
