const {StateStore} = require('../typewheels/statestore')
const Chatbase = require(process.env.CHATBASE_BACKEND)
const {PromiseStream} = require('@vlab-research/steez')
const {DBStream} = require('./pgstream')
const {TokenStore} = require('../typewheels/tokenstore')
const {Machine} = require('../typewheels/transition')

async function query(pool, userid, lim) {
  const query = `WITH r as (SELECT *, ROW_NUMBER() OVER (ORDER BY timestamp) AS row_number
                 FROM messages ORDER BY timestamp ASC)
                 SELECT * FROM r
                 WHERE row_number > $2
                     AND userid = $1
                 ORDER BY row_number
                 LIMIT 100;`

  const res = await pool.query(query, [userid, lim])
  const final = res.rows.slice(-1)[0]
  if (!final) return [null, null]
  return [res.rows, final['row_number']]
}

const userid = process.argv.slice(2)[0]
if (!userid) throw new Error('GIVE ME USERID!')

const fn = (lim) => query(chatbase.pool, userid, lim)
const stream = new DBStream(fn, 0)

const chatbase = new Chatbase()
const emptyBase = { get: () => [], pool: chatbase.pool }
const stateStore = new StateStore(emptyBase)
const tokenStore = new TokenStore(chatbase.pool)
const machine = new Machine('600s', tokenStore)

stream
  .pipe(new PromiseStream(async ({userid:userId, content:event}) => {

    const state = await stateStore.getState(userId, event)
    const { newState, actions, output } = await machine.transition(state, userId, event)

    console.log('STATE:\n', state, '-----------------------')
    console.log('EVENT:\n', JSON.parse(event, null, 4), '-----------------------')
    console.log('OUTPUT\n: ', output, '-----------------------')
    console.log('ACTIONS:\n', actions, '-----------------------')
    console.log('NEW STATE:\n', newState, '-----------------------')

    await stateStore.updateState(userId, newState)
  }))
