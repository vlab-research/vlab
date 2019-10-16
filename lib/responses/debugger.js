const Cacheman = require('cacheman')
const {exec, apply, update} = require('../typewheels/machine')
const {StateStore} = require('../typewheels/statestore')
const Chatbase = require(process.env.CHATBASE_BACKEND)
const {PromiseStream} = require('@vlab-research/steez')
const QueryStream = require('pg-query-stream')

const chatbase = new Chatbase()
const emptyBase = { get: () => [], pool: chatbase.pool }
const stateStore = new StateStore(emptyBase)

const userid = process.argv.slice(2)[0]
if (!userid) throw new Error('GIVE ME USERID!')


const cache = new Cacheman()
const getFormCached = form => cache.wrap(`form:${form}`, () => getForm(form), process.env.FORM_CACHED || '60s')
const getUserCached = id => cache.wrap(`user:${id}`, () => getUserInfo(id), process.env.USER_CACHED || '60s')


const query = new QueryStream('SELECT * FROM messages WHERE userid = $1 ORDER BY timestamp ASC;', [userid])

chatbase.pool.connect()
  .then(client => {
    client.query(query)
      .on('end', async () => {
        await client.release()
        await chatbase.pool.end()
      })
      .pipe(new PromiseStream(async ({userid:userId, content:e}) => {

        const state = await stateStore.getState(userId, e)
        console.log('STATE:\n', state, '-----------------------')

        const parsedEvent = stateStore.parseEvent(e)
        const output = exec(state, parsedEvent)

        console.log('OUTPUT\n: ', output, '-----------------------')
        const newState = apply(state, output)

        const formId = newState.forms.slice(-1)[0]
        const form = await getFormCached(formId)
        const user = await getUserCached(userId)

        const actions = act({form, user}, state, output)

        console.log('ACTIONS:\n', actions, '-----------------------')

        await stateStore.updateState(userId, newState)
      }))

})
