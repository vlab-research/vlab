const Cacheman = require('cacheman')
const Kafka = require('node-rdkafka')
const util = require('util')
const {exec, apply, update} = require('./typewheels/machine')
const {FieldError} = require('./typewheels/form')
const {getForm} = require('./typewheels/typeform')
const {PromiseStream} = require('@vlab-research/steez')
const {EventStore} = require('@vlab-research/eventstore')
const {StateStore} = require('./typewheels/statestore')

const cache = new Cacheman()
const getFormCached = form => cache.wrap(`form:${form}`, () => getForm(form), '3600s')

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

// quick hack to work without backend, as we have multiple databases
// right now!
class Chatbase {
  async get (key) {}
}

// const Chatbase = require(process.env.CHATBASE_BACKEND)
const stateStore = new StateStore(new Chatbase())
console.log('event store and chatbase created')

const write = async (msg) => {
  const userId = msg.key.toString()
  const e = msg.value.toString()

  try {

    const state = await stateStore.getState(userId, e)
    const parsedEvent = stateStore.parseEvent(e)
    const output = exec(state, parsedEvent)
    const newState = apply(state, output)

    const flowId = newState.forms.length
    const formId = newState.forms.slice(-1)[0]

    const form = await getFormCached(formId)
    const upd = output && update(output)

    if (upd) {
      const [q, value] = upd
      const timestamp = parsedEvent.timestamp
      const [qidx, {title, ref}] = getField(form, q)
      const vals = [formId, flowId, userId, ref, qidx, title, value, new Date(timestamp)]
      await put(vals)
    }

    stateStore.updateState(userId, newState)

  } catch (error) {
    if (error instanceof FieldError) {

    } else {
      console.warn(error)
      console.log('ERROR OCCURRED DURING EVENT: ')
      console.log(util.inspect(JSON.parse(e), null, 8))
    }
  }

  // consumer.commitMessage(message)

}

const dbStream = new PromiseStream(write, {
  highWaterMark: 200
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
  const query = `INSERT INTO responses(formid, flowid, userid, question_ref, question_idx, question_text, response, timestamp)
		   values($1, $2, $3, $4, $5, $6, $7, $8)
		   ON CONFLICT(userid, timestamp) DO NOTHING`

  return pool.query(query, vals)
}



function getField(form, ref) {
  if (!form.fields.length) {
    throw new FieldError(`This form has no fields: ${form.id}`)
  }

  const idx = form.fields.map(({ref}) => ref).indexOf(ref)
  const field = form.fields[idx]

  if (!field) {
    throw new FieldError(`Could not find the requested field, ${field}, in our form!`)
  }

  return [idx, field]
}
