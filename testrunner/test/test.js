require('chai').should()
const sender = require('../sender.js')
const {makeMocks, makeEcho, makePostback, makeTextResponse} = require('./mocks')
const Kafka = require('node-rdkafka')
const uuid = require('uuid');

describe('Test Bot flow Survey Integration Testing', () => {
  const kafkaOpts = {
    'metadata.broker.list': process.env.KAFKA_BROKERS,
    'group.id': process.env.KAFKA_GROUP_ID,
    'client.id': process.env.KAFKA_GROUP_ID,
    'enable.auto.commit': true
  }

  const stream = new Kafka.createReadStream(kafkaOpts,
                                      {},
                                      { topics: ['facebot']})


  let testFlow = [];
  let messages = [];
  let userId = null;
  let bindedDone;

  before(() => {
    console.log('Test starting!');
  });

  beforeEach(() => {
    userId = uuid()
  })

  after(() => {
    console.log('Test finished!');
  });

  it('Test chat flow with logic jump "Yes"',  (done) => {
    bindedDone = done.bind(this)

    const mocks = makeMocks(userId)

    testFlow = [
      [mocks.acceptMessage, [makePostback(mocks.acceptMessage, userId, 0)]],
      [mocks.questionMessage, [makePostback(mocks.questionMessage, userId, 0)]],
      [mocks.funMessage, [makeTextResponse(userId, 'LOL')]],
      [mocks.thanksMessage, []],
      [mocks.endMessage, []],
    ];

    sender(mocks.referral);

  }).timeout(20000);

  it('Test chat flow with logic jump "No"',  (done) => {
    bindedDone = done.bind(this)
    const mocks = makeMocks(userId)

    testFlow = [
      [mocks.acceptMessage, [makePostback(mocks.acceptMessage, userId, 0)]],
      [mocks.questionMessage, [makePostback(mocks.questionMessage, userId, 1)]],
      [mocks.boringMessage, []],
      [mocks.endMessage, []],
    ];

    sender(mocks.referral);

  }).timeout(20000);


  stream.on('data', async (message) => {
    const msg = JSON.parse(message.value.toString()).message
    const [get, gives] = testFlow[messages.length]

    messages.push(msg)
    msg.should.eql(get);

    await sender(makeEcho(get, userId))

    for (let giv of gives) {
      await sender(giv);
    }

    if (messages.length == testFlow.length) {
      messages= [];
      bindedDone();
    }
  })

});
