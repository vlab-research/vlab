const util = require('util')
const Cacheman = require('cacheman')
const Kafka = require('node-rdkafka')
const {Machine} = require('./typewheels/form')
const {getCurrentForm, getMessage, getState} = require('./typewheels/machine')
const {KeyedStreamer, PromiseStream} = require('@vlab-research/steez')
const {EventStore} = require('@vlab-research/eventstore')

const {sendMessage, getUserInfo } = require('./messenger')
const {getForm} = require('./typewheels/typeform')

// Cache form from Typeform
const cache = new Cacheman()
const getFormCached = form => cache.wrap(`form:${form}`, () => getForm(form), process.env.FORM_CACHED || '60s')
const getUserCached = id => cache.wrap(`user:${id}`, () => getUserInfo(id), process.env.USER_CACHED || '60s')

// Does all the work
async function processor (message, consumer, eventStore) {
  const userId = message.key.toString()
  const event = message.value.toString()

  try {
    const events = await eventStore.getEvents(userId, event)
    const [formId, log] = getCurrentForm(events)

    const form = await getFormCached(formId)
    const user = await getUserCached(userId)

    // get user info cached too...
    const actions = getMessage(log, form, user)

    for (action of actions) {
      await sendMessage(userId, action, cache)
      console.log(action)
    }

    consumer.commitMessage(message)
    eventStore.put(userId, event)
  }

  catch (e) {
    console.error('Error from ReplyBot: ', e.message)
    console.error(e.stack)
  }
}

// EventStore with chatbase backend
const Chatbase = require(process.env.CHATBASE_BACKEND)
const eventStore = new EventStore(new Chatbase())

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
  'client.id': 'replybot',
  'enable.auto.commit': false,
  'metadata.broker.list': `${process.env.KAFKA_BROKER}:${process.env.KAFKA_PORT}`
}
const stream = new Kafka.createReadStream(kafkaOpts,
                                          { 'auto.offset.reset': 'earliest' },
                                          { topics: [ process.env.REPLYBOT_EVENT_TOPIC ]})

// Run!
stream
  .pipe(processStream)
  .on('error', err => {
    console.error(err)
  })

// ------- SHUT DOWN --------
// TODO: Cleanup!
const signals = {
  'SIGHUP': 1,
  'SIGINT': 2,
  'SIGTERM': 15
}

for (let [signal, value] in signals) {
  process.on(signal, () => {
    stream.consumer.disconnect()
    stream.consumer.on('disconnected', () => {
      process.exit(128 + value)
    })
  })
}
