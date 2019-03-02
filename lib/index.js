const util = require('util')
const Cacheman = require('cacheman')
const Kafka = require('node-rdkafka')
const {Machine} = require('./typewheels/form')
const {getCurrentForm, getMessage, getState} = require('./typewheels/machine')
const {KeyedStreamer, PromiseStream} = require('./streams')
const {EventStore} = require('./eventstore')
const gcs = require('./chatbase-gcs')
const {sendMessage, getUserInfo } = require('./messenger')
const {getForm} = require('./typewheels/typeform')


// Cache form from Typeform
const cache = new Cacheman()
const getFormCached = form => cache.wrap(`form:${form}`, () => getForm(form), '60s')
const getUserCached = id => cache.wrap(`user:${id}`, () => getUserInfo(id), '60s')

// Does all the work
async function processor (message, consumer, eventStore) {
  const userId = message.key.toString()
  const event = message.value.toString()

  try {
    const events = await eventStore.getEvents(userId, event)
    const [formId, log] = getCurrentForm(events.map(JSON.parse))
    const form = await getFormCached(formId)
    const user = await getUserCached(userId)

    // get user info cached too...
    const action = getMessage(log, form, user)

    if (action) {
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
  'client.id': 'replybot',
  'metadata.broker.list': `${process.env.KAFKA_BROKER}:${process.env.KAFKA_PORT}`
}
const stream = new Kafka.createReadStream(kafkaOpts, {}, { topics: ['chat-events']})

// Run!
stream
  .pipe(processStream)
  .on('error', err => {
    console.error(err)
  })
