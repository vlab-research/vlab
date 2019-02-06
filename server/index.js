const util = require('util')
const request = require('request')
const r2 = require('r2')
const {getForm, verifyToken, getUser} = require('./services')
const {Machine} = require('./typewheels/form')
const {getState} = require('./typewheels/typewheels')
const farmhash = require('farmhash')
const Cacheman = require('cacheman')
const Redis = require('ioredis')
const Queue = require('bull')
const Kafka = require('node-rdkafka')

async function sendMessage(recipientId, response, cache) {

  // quick hack to avoid double sending!
  // const i = farmhash.hash32(JSON.stringify(response))
  // if (await cache.get(`sent:${i}`)) return
  // await cache.set(`sent:${i}`, true, 5)

  request({
    url: 'https://graph.facebook.com/v3.2/me/messages',
    headers: { Authorization: `Bearer ${process.env.PAGE_ACCESS_TOKEN}`},
    method: 'POST',
    json: {
      recipient: { id: recipientId },
      message: response,
    }
  }, function (error, response, body) {
    if (error) {
      console.log('Error sending message: ', error);
    } else if (response.body.error) {
      console.log('Error: ', response.body.error);
    }
  })
}

const cache = new Cacheman()
const kafkaOpts = {
  'group.id': 'replybot',
  'metadata.broker.list': 'spinaltap-kafka:9092'
}

// var consumer = new Kafka.KafkaConsumer(kafkaOpts, {})

// consumer.connect();

// consumer
//   .on('ready', () => {
//     consumer.subscribe(['chat-events'])
//     consumer.consume()
//   })
//   .on('data', data => {
//     console.log(data)
//     console.log(JSON.parse(data.value.toString()));
//   });

const db = {}

const stream = new Kafka.createReadStream(kafkaOpts, {}, { topics: ['chat-events']})

stream.on('data', async (message) => {

  try {

    const user = message.key.toString()
    const event = message.value.toString()

    console.log(`message recieved from ${user}`)

    if (db[user]) {
      db[user] = [...db[user], event]
    } else {

      // if not, get from db (filestore!)

      db[user] = [event]
    }

    const log = db[user].map(JSON.parse)

    const state = getState(log)
    const machine = new Machine()

    // TODO
    if (!state) throw new Error('User does not have any current form!')

    const form = await getFormCached(state.form)
    const action = machine.exec(state, form, log)

    if (action) {
      await sendMessage(user, action, cache)
    }

    stream.consumer.commitMessage(message)

  } catch (error) {
    console.error('[ERR] processJob: ', error)
  }
}).on('error', err => {
  console.error(err)
})


const getFormCached = form => cache.wrap('form', () => getForm(form), '30s')

// q.process(async ({data:event}, done) => {

// })
