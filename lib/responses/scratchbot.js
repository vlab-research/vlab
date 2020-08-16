const {BotSpine} = require('@vlab-research/botspine')
const {Responser} = require('./responser')
const Chatbase = require(process.env.CHATBASE_BACKEND)


const chatbase = new Chatbase()
console.log('SCRATCHBOT: chatbase created')

for (let i = 0; i < 6; i++) {
  const responser = new Responser(chatbase)
  const spine = new BotSpine('scratchbot')

  spine.source()
    .pipe(spine.transform(responser.write.bind(responser)))
    .pipe(spine.sink())
    .on('error', err => {
      console.error(err)
    })
}
