const Cacheman = require('cacheman')
const Kafka = require('node-rdkafka')
const util = require('util')

const {getState, exec, update} = require('./typewheels/machine')
const {FieldError, getForm} = require('./typewheels/form')
const {splitLogsByForm, parseLogJSON} = require('./typewheels/utils')

const {PromiseStream} = require('@vlab-research/steez')
const {EventStore} = require('@vlab-research/eventstore')


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
const eventStore = new EventStore(new Chatbase())
console.log('event store and chatbase created')


// update function used internally to update qa of state
// use that same function externally here
// then leave qa inside the state

// get state



// update state

const write = async (msg) => {
  const userId = msg.key.toString()
  const e = msg.value.toString()

  try {
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
      const [qIdx, {title, ref}] = getField(form, q)
      const vals = [formId, flowId, userId, ref, qidx, title, value, new Date(timestamp)]
      await put(vals)
    }

  } catch (error) {
    if (error instanceof FieldError) {

    } else {
      console.warn(error)
      console.log('ERROR OCCURRED DURING EVENT: ')
      console.log(util.inspect(JSON.parse(e), null, 8))
    }
  }

  eventStore.put(userId, e)
  // stream.consumer.commitMessage(msg)
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
		   values($1, $2, $3, $4, $5, $6, $7)
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
