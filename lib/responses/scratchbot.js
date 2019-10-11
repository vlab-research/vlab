const {BotSpine} = require('@vlab-research/botspine')
const {Responser} = require('./responser')
const Chatbase = require(process.env.CHATBASE_BACKEND)

const chatbase = new Chatbase()
const responser = new Responser(chatbase)
const spine = new BotSpine('scratchbot')

console.log('SCRATCHBOT: event store and chatbase created')

spine.source()
  .pipe(spine.transform(responser.write))
  .pipe(spine.sink())
  .on('error', err => {
    console.error(err)
  })
