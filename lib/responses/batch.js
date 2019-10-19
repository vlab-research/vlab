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
    console.log('FINISHED WRITING')
    await chatbase.pool.end()
  })
  .pipe(new PromiseStream(({userid, content}) => {
    i++
    console.log(i)
    return responser.write({key:userid, value:content})
    // return Promise.resolve(true)

  }))
  .on('error', (err) => {
    console.log('emitted error...')
    console.error(err)
  })
