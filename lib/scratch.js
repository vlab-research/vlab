const Cacheman = require('cacheman')
const Kafka = require('node-rdkafka')

const {getState, exec, update} = require('./typewheels/machine')
const {getField} = require('./typewheels/form')
const {splitLogsByForm, parseLogJSON} = require('./typewheels/utils')
const {PromiseStream} = require('@vlab-research/steez')
const {EventStore} = require('@vlab-research/eventstore')

const {getForm} = require('./typewheels/typeform')

const cache = new Cacheman()
const getFormCached = form => cache.wrap(`form:${form}`, () => getForm(form), process.env.FORM_CACHED || '60s')

// KAFKA
const kafkaOpts = {
  'group.id': 'scratchbot',
  'client.id': 'scratchbot',
  'enable.auto.commit': false,
  'metadata.broker.list': `${process.env.KAFKA_BROKER}:${process.env.KAFKA_PORT}`
}
const stream = new Kafka.createReadStream(kafkaOpts,
                                          { 'auto.offset.reset': 'earliest' },
                                          { topics: [ process.env.REPLYBOT_EVENT_TOPIC ]})

class Chatbase {
  async get (key) {}
  async put (key, message, timestamp) {}
}

const eventStore = new EventStore(new Chatbase())

console.log('event store and chatbase created')

const write = async (msg) => {
  const userId = msg.key.toString()
  const e = msg.value.toString()
  const events = await eventStore.getEvents(userId, e)

  const forms = splitLogsByForm(parseLogJSON(events))
  const flowId = forms.length - 1

  const [formId, log] = forms.pop()
  const form = await getFormCached(formId)

  const event = log.slice(-1)[0]
  const state = getState(log.slice(0,-1))

  const output = exec(state, event)
  const upd = output && update(output)

  if (upd) {
    const [q, {value, timestamp}] = upd
    const {title, ref} = getField({form}, q)
    const vals = [formId, flowId, userId, title, ref, value, new Date(timestamp)]
    await put(vals)
    console.log(vals)
  }

  eventStore.put(userId, e)
  stream.consumer.commitMessage(msg)
}

const dbStream = new PromiseStream(write, {
  highWaterMark: 20
})

stream
  .pipe(dbStream)
  .on('error', err => {
    console.error(err)
  })

/*
   TODO: CLEAN THIS UP!
   MOVE TO CHATBASE?????
*/

const { Pool } = require('pg')
const pgConfig = {user: process.env.CHATBASE_USER,
                  host: process.env.CHATBASE_HOST,
                  database: process.env.CHATBASE_DATABASE,
                  password: process.env.CHATBASE_PASSWORD,
                  port: process.env.CHATBASE_PORT}

const pool = new Pool(pgConfig)

function put (vals) {
  const query = `INSERT INTO responses(formid, flowid, userid, question_text, question_ref, response, timestamp)
		   values($1, $2, $3, $4, $5, $6, $7)
		   ON CONFLICT(userid, timestamp) DO NOTHING`

  return pool.query(query, vals)
}
