const {Responser} = require('./responser')
const Chatbase = require(process.env.CHATBASE_BACKEND)
const {PromiseStream} = require('@vlab-research/steez')
const QueryStream = require('pg-query-stream')

const chatbase = new Chatbase()
const emptyBase = { get: () => [], pool: chatbase.pool }
const responser = new Responser(emptyBase)
const query = new QueryStream('SELECT * FROM messages ORDER BY timestamp ASC;')

chatbase.pool.connect()
  .then(client => {
    client.query(query)
      .on('end', async () => {
        await client.release()
        await chatbase.pool.end()
      })
      .pipe(new PromiseStream(({userid, content}) => responser.write({key:userid, value:content})))

})
