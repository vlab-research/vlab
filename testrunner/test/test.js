require('chai').should()
const sender = require('../sender.js')
const {makeMocks, makeEcho, makePostback, makeTextResponse, makeReferral, getFields} = require('./mocks')
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

  it('Waits for external event when there is no event',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/Ep5wnS.json')

    testFlow = []

    testFlow = [
      [fields[0], [makePostback(fields[0], userId, 0)]],
      [fields[1], []]
    ]

    sender(makeReferral(userId, 'Ep5wnS'))

  }).timeout(20000);

  // it('Waits for external event and continues after event',  (done) => {
  //   bindedDone = done.bind(this)
  //   const fields = getFields('forms/Ep5wnS.json')

  //   testFlow = []

  //   testFlow = [
  //     [fields[0], [makePostback(fields[0], userId, 0)]],
  //     [fields[1], []], // add external event
  //     [fields[2], [makePostback(fields[0], userId, 0)]]
  //     [fields[3], []]
  //   ]

  //   sender(makeReferral(userId, 'Ep5wnS'))

  // }).timeout(20000);

  it('Test chat flow with logic jump "Yes"',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/LDfNCy.json')

    testFlow = [
      [fields[0], [makePostback(fields[0], userId, 0)]],
      [fields[1], [makePostback(fields[1], userId, 0)]],
      [fields[2], [makeTextResponse(userId, 'LOL')]],
      [fields[4], []],
      [fields[5], []],
    ]

    sender(makeReferral(userId, 'LDfNCy'))

  }).timeout(20000);

  it('Test chat flow with logic jump "No"',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/LDfNCy.json')

    testFlow = [
      [fields[0], [makePostback(fields[0], userId, 0)]],
      [fields[1], [makePostback(fields[1], userId, 1)]],
      [fields[3], []],
      [fields[5], []],
    ];

    sender(makeReferral(userId, 'LDfNCy'));

  }).timeout(20000);

  stream.on('data', async (message) => {
    const msg = JSON.parse(message.value.toString()).message
    const [get, gives] = testFlow[messages.length]
    messages.push(msg)

    // console.log('FIELD ------', messages.length)
    // console.log(msg)
    // console.log(get)

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
