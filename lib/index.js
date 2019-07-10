const util = require('util')
const Cacheman = require('cacheman')
const Kafka = require('node-rdkafka')
const {exec, apply, act} = require('./typewheels/machine')
const {KeyedStreamer, PromiseStream} = require('@vlab-research/steez')
const {StateStore} = require('./typewheels/statestore')
const {sendMessage, getUserInfo } = require('./messenger')
const {getForm} = require('./typewheels/typeform')

// Cache form from Typeform
const cache = new Cacheman()
const getFormCached = form => cache.wrap(`form:${form}`, () => getForm(form), process.env.FORM_CACHED || '60s')
const getUserCached = id => cache.wrap(`user:${id}`, () => getUserInfo(id), process.env.USER_CACHED || '60s')

// Does all the work
async function processor (message, consumer, stateStore) {
  const userId = message.key.toString()
  const event = message.value.toString()

  try {
    const state = await stateStore.getState(userId, event)
    console.log('STATE: ', state)

    const parsedEvent = stateStore.parseEvent(event)
    const output = exec(state, parsedEvent)
    console.log('OUTPUT: ', output)
    const newState = apply(state, output)


    const formId = newState.forms.slice(-1)[0]

    const form = await getFormCached(formId)
    const user = await getUserCached(userId)

    const actions = act({form, user}, state, output)

    for (action of actions) {

      await sendMessage(userId, action, cache)
      console.log(action)
    }

    consumer.commitMessage(message)
    stateStore.updateState(userId, newState)
  }

  catch (e) {
    console.error('Error from ReplyBot: ', e.message)
    console.error(e.stack)
  }
}

// EventStore with chatbase backend
const Chatbase = require(process.env.CHATBASE_BACKEND)
const stateStore = new StateStore(new Chatbase())

// Create stream to handle back pressure
const subStreamer = () => new PromiseStream(m => processor(m,
                                                           stream.consumer,
                                                           stateStore))
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
