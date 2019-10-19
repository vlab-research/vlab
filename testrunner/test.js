require('chai').should()
const sender = require('./sender.js')
const {makeMocks, makeEcho, makeQR, makePostback, makeTextResponse, makeReferral, makeSynthetic, getFields} = require('@vlab-research/mox')
const uuid = require('uuid');
const zmq = require('zeromq')
const sock = zmq.socket('sub');
const farmhash = require('farmhash');
const util = require('util');

sock.connect('tcp://gbv-facebot:4000');
sock.subscribe('messages');

describe('Test Bot flow Survey Integration Testing', () => {

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
    const fields = getFields('forms/LDfNCy.json')

    testFlow = [
      [fields[0], [makePostback(fields[0], userId, 0)]],
      [fields[1], [makePostback(fields[1], userId, 0)]],
      [fields[2], [makeTextResponse(userId, 'LOL')]],
      [fields[4], []],
      [fields[5], []],
    ]

    sender(makeReferral(userId, '23'))

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

    sender(makeReferral(userId, '23'));

  }).timeout(20000);


  it('Test chat flow with logic jump from previous question',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/jISElk.json')

    testFlow = [
      [fields[0], [makeQR(fields[0], userId, 1)]],
      [fields[1], [makeQR(fields[1], userId, 5)]],
      [fields[2], [makeTextResponse(userId, 'LOL')]],
      [fields[4], []],
      [fields[5], []],
    ]

    sender(makeReferral(userId, '175'))

  }).timeout(20000);

  it('Test chat flow logic jump from hidden seed_2 field', (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/nFgfNE.json')

    const makeId = () => {
      const uid = uuid()
      const suitable = farmhash.fingerprint32('128' + uid) % 2 === 0;
      return suitable ? uid : makeId();
    }

    userId = makeId()

    testFlow = [
      [fields[0], [makeQR(fields[0], userId, 1)]],
      [fields[1], [makePostback(fields[1], userId, 0)]],
      [fields[3], []],
    ]

    sender(makeReferral(userId, '128'))

  }).timeout(20000);


  it('Waits for external event and continues after event',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/Ep5wnS.json')

    testFlow = [
      [fields[0], [makePostback(fields[0], userId, 0)]],
      [fields[1], [makeSynthetic(userId, { type: 'external', value: {type: 'moviehouse:play', id: 164118668 }})]],
      [fields[2], [makePostback(fields[2], userId, 0)]],
      [fields[3], []]
    ]

    sender(makeReferral(userId, '463'))

  }).timeout(20000);


  it('Sends timeout message response when interrupted in a timeout, then waits',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/vHXzrh.json')

    testFlow = [
      [fields[0], [makeTextResponse(userId, 'LOL')]],
      [{ text: 'Please wait!', metadata: '{"repeat":true,"ref":"bd2b2376-d722-4b51-8e1e-c2000ce6ec55"}'}, []],
      [fields[0], []],
      [fields[1], [makeTextResponse(userId, 'LOL')]],
      [fields[2], []],
    ]

    sender(makeReferral(userId, '519'))

  }).timeout(180000);


  sock.on('message', async (_, message) => {
    const msg = JSON.parse(message.toString()).message
    const [get, gives] = testFlow[messages.length]
    messages.push(msg)

    try {
      msg.should.eql(get);
    }
    catch (e) {
      console.log(util.inspect(msg, null, 8))
      console.log(util.inspect(get, null, 8))
      console.error(e);
      throw e;
    }

    await sender(makeEcho(get, userId))

    for (let giv of gives) {
      await sender(giv);
    }

    if (messages.length == testFlow.length) {
      messages = [];
      bindedDone();
    }
  })

});
