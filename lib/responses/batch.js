const {Responser} = require('./responser')
const Chatbase = require(process.env.CHATBASE_BACKEND)
const {PromiseStream} = require('@vlab-research/steez')
const QueryStream = require('pg-query-stream')
const {DBStream, messagesQuery} = require('./pgstream')

const chatbase = new Chatbase()
const emptyBase = { get: () => [], pool: chatbase.pool }
const responser = new Responser(emptyBase)

const fn = (lim) => messagesQuery(chatbase.pool, lim)


//. start from... 0?
const stream = new DBStream(fn, 0)

i = 0

stream
  .on('end', async () => {
    console.log(`FINISHED WRITING ${i} EVENTS`)
    setTimeout(async () => {
      await chatbase.pool.end()
    }, 5000)
  })
  .pipe(new PromiseStream(({userid, content}) => {
    i++
    return responser.write({key:userid, value:content})
  }))
  .on('error', (err) => {
    console.log('emitted error...')
    console.error(err)
  })
