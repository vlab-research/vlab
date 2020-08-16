const {BotSpine} = require('@vlab-research/botspine')
const {Responser} = require('./responser')
const Chatbase = require(process.env.CHATBASE_BACKEND)


console.log('SCRATCHBOT: event store and chatbase created')

for (let i = 0; i < 6; i++) {
  const chatbase = new Chatbase()
  const responser = new Responser(chatbase)
  const spine = new BotSpine('scratchbot')

  spine.source()
    .pipe(spine.transform(responser.write.bind(responser)))
    .pipe(spine.sink())
    .on('error', err => {
      console.error(err)
    })
}
