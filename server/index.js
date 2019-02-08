const util = require('util')
const Cacheman = require('cacheman')
const Kafka = require('node-rdkafka')
const {Machine} = require('./typewheels/form')
const {getState} = require('./typewheels/typewheels')
const {KeyedStreamer, PromiseStream} = require('./utils')
const {sendMessage, getForm, getUser, getEvents} = require('./services')

// KAFKA
const kafkaOpts = {
  'group.id': 'replybot',
  'metadata.broker.list': `{process.env.KAFKA_BROKER:process.env.KAFKA_PORT}`
}
const stream = new Kafka.createReadStream(kafkaOpts, {}, { topics: ['chat-events']})

// Cache form from Typeform
const cache = new Cacheman()
const getFormCached = form => cache.wrap('form', () => getForm(form), '30s')

// Does all the work
async function process (message, consumer) {
  const user = message.key.toString()
  const event = message.value.toString()
  console.log(`message recieved from ${user}`)

  const events = await getEvents(user, event)
  const log = events.map(JSON.parse)
  const state = getState(log)
  const form = await getFormCached(state.form)

  const machine = new Machine()
  const action = machine.exec(state, form, log)

  if (action) {
    await sendMessage(user, action, cache)
  }

  consumer.commitMessage(message)
}

// Create stream to handle back pressure
const subStreamer = () => new PromiseStream(m => process(m, stream.consumer))
const processStream = new KeyedStreamer(m => m.key.toString(),
                                        subStreamer,
                                        {highWaterMark: 200})

// Run!
stream
  .pipe(processStream)
  .on('error', err => {
    console.error(err)
  })
