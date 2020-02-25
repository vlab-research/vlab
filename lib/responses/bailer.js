const Chatbase = require(process.env.CHATBASE_BACKEND)
const {PromiseStream} = require('@vlab-research/steez')
const {DBStream, messagesQuery} = require('./pgstream')
const {Machine} = require('../typewheels/transition')
const {StateStore} = require('../typewheels/statestore')
const _ = require('lodash')
// const emptyBase = { get: () => [], pool: chatbase.pool }
// const responser = new Responser(emptyBase)

// DB STREAM
const chatbase = new Chatbase()
const stateStore = new StateStore(chatbase)
const machine = new Machine('600s')

const fn = (lim) => messagesQuery(chatbase.pool, lim)
const stream = new DBStream(fn, 0)

let i = 0

stream
  .on('end', async () => {
    setTimeout(async () => {
      await chatbase.pool.end()
    }, 5000)
  })
  .pipe(new PromiseStream(({userid:userId, content:e}) => {






  }))
  .on('error', (err) => {
    console.log('emitted error...')
    console.error(err)
  })
