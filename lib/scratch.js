const Cacheman = require('cacheman')
const util = require('util')
const {exec, apply, update} = require('./typewheels/machine')
const {FieldError} = require('./typewheels/form')
const {getForm} = require('./typewheels/typeform')
const {PromiseStream} = require('@vlab-research/steez')
const {EventStore} = require('@vlab-research/eventstore')
const {StateStore} = require('./typewheels/statestore')
const {BotSpine} = require('@vlab-research/botspine')

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

class Responser {
  constructor(stateStore) {
    this.stateStore = stateStore
    this.cache = new Cacheman()
    this.getForm = form => this.cache.wrap(`form:${form}`, () => getForm(form), '3600s')
  }

  async updateStore(userId, e) {
    let vals

    const state = await this.stateStore.getState(userId, e)
    const parsedEvent = this.stateStore.parseEvent(e)
    const output = exec(state, parsedEvent)
    const newState = apply(state, output)

    const flowId = newState.forms.length
    const formId = newState.forms.slice(-1)[0]

    const form = await this.getForm(formId)
    const upd = output && update(output)

    if (upd) {
      const [q, value] = upd
      const timestamp = parsedEvent.timestamp
      const [qidx, {title, ref}] = getField(form, q)
      vals = [formId, flowId, userId, ref, qidx, title, value, new Date(timestamp)]
    }

    await this.stateStore.updateState(userId, newState)

    return vals
  }
}


const Chatbase = require(process.env.CHATBASE_BACKEND)
const chatbase = new Chatbase()
const stateStore = new StateStore(chatbase)
const responser = new Responser(stateStore)
console.log('event store and chatbase created')


const write = async ({key, value}) => {
  const userId = key
  const e = value

  try {
    const vals = responser.updateStore(userId, e)
    if (vals) {
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
}

const spine = new BotSpine('scratchbot')

spine.source()
  .pipe(spine.transformer(write))
  .pipe(spine.sink())
  .on('error', err => {
    console.error(err)
  })

/*
   TODO: CLEAN THIS UP!
   MOVE TO CHATBASE?????
*/


function put (vals) {
  const query = `INSERT INTO responses(formid, flowid, userid, question_ref, question_idx, question_text, response, timestamp)
		   values($1, $2, $3, $4, $5, $6, $7, $8)
		   ON CONFLICT(userid, timestamp) DO NOTHING`

  return chatbase.pool.query(query, vals)
}
