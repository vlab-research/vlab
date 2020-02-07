require('chai').should()
const sender = require('./sender.js')
const {makeMocks, makeEcho, makeQR, makePostback, makeTextResponse, makeReferral, makeSynthetic, getFields} = require('@vlab-research/mox')
const uuid = require('uuid');
const zmq = require('zeromq')
const sock = zmq.socket('sub');
const farmhash = require('farmhash');
const util = require('util');
const {seed} = require('./seed-db');


// SETUP -----------------------------------
sock.connect('tcp://gbv-facebot:4000');
sock.subscribe('messages');

const Chatbase = require(process.env.CHATBASE_BACKEND)
const chatbase = new Chatbase()

async function getResponses(userid) {
  const {rows} = await chatbase.pool.query('SELECT * FROM responses WHERE userid=$1 ORDER BY timestamp ASC', [userid])
  return rows
}

const snooze = ms => new Promise(resolve => setTimeout(resolve, ms));

function makeRepeat(field, text) {
  const ref = JSON.parse(field.metadata).ref
  return { text: text,
           metadata: JSON.stringify({ repeat: true, ref  }) }
}


describe('Test Bot flow Survey Integration Testing', () => {

  let testFlow = [];
  let messages = [];
  let userId = null;
  let bindedDone;

  before(async () => {
    await seed(chatbase);
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

    sender(makeReferral(userId, 'jISElk'))

  }).timeout(20000);

  it('Test chat flow logic jump from hidden seed_2 field', (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/nFgfNE.json')

    const makeId = () => {
      const uid = uuid()
      const suitable = farmhash.fingerprint32('nFgfNE' + uid) % 2 === 0;
      return suitable ? uid : makeId();
    }

    userId = makeId()

    testFlow = [
      [fields[0], [makeQR(fields[0], userId, 1)]],
      [fields[1], [makePostback(fields[1], userId, 0)]],
      [fields[3], []],
    ]

    sender(makeReferral(userId, 'nFgfNE'))

  }).timeout(20000);

  it('Test chat flow with validation failures',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/ciX4qo.json')

    const repeatPhone = makeRepeat(fields[0], 'Sorry, please enter a valid mobile number.')
    const repeatEmail = makeRepeat(fields[1], 'Sorry, please enter a valid email address.')

    testFlow = [
      [fields[0], [makeTextResponse(userId, '23345')]],
      [repeatPhone, []],
      [fields[0], [makeTextResponse(userId, '+918888000000')]],
      [fields[1], [makeTextResponse(userId, 'foo')]],
      [repeatEmail, []],
      [fields[1], [makeTextResponse(userId, 'foo@gmail.com')]],
      [fields[2], []]
    ];

    sender(makeReferral(userId, 'ciX4qo'));

  }).timeout(20000);

  it('Test chat flow with stitched forms: stitches and maintains seed"',  (done) => {

    const makeId = () => {
      const uid = uuid()
      const suitable = farmhash.fingerprint32('Llu24B' + uid) % 5 === 0;
      return suitable ? uid : makeId();
    }

    userId = makeId()


    const fieldsA = getFields('forms/Llu24B.json')
    const fieldsB = getFields('forms/tKG55U.json')

    testFlow = [
      [fieldsA[0], [makeTextResponse(userId, 'LOL')]],
      [fieldsA[1], []],
      [fieldsB[0], [makePostback(fieldsB[0], userId, 0)]],
      [fieldsB[2], []],
    ]

    sender(makeReferral(userId, 'Llu24B'))

    bindedDone = async () => {

      // TODO: make sure we only get from latest test cycle

      // await snooze(1000) // Give scratchbot a second to write

      // const res = await getResponses(userId)
      // res.length.should.equal(2)
      // res.map(r => r['response']).should.include('LOL')
      // res.map(r => r['response']).should.include('true')
      // res.map(r => r['parent_shortcode']).should.eql(['Llu24B', 'Llu24B'])
      done()
    }

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

    sender(makeReferral(userId, 'Ep5wnS'))

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

    sender(makeReferral(userId, 'vHXzrh'))

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
