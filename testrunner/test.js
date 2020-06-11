require('chai').should()
const sender = require('./sender.js')
const {makeMocks, makeEcho, makeQR, makePostback, makeTextResponse, makeReferral, makeSynthetic, getFields, makeNotify} = require('@vlab-research/mox')
const uuid = require('uuid');

const zmq = require('zeromq')
const sock = zmq.socket('rep')


const farmhash = require('farmhash');
const util = require('util');
const {seed} = require('./seed-db');


// SETUP -----------------------------------
sock.connect('tcp://gbv-facebroker:4001')

const Chatbase = require(process.env.CHATBASE_BACKEND)
const chatbase = new Chatbase()

async function getResponses(userid) {
  const {rows} = await chatbase.pool.query('SELECT * FROM responses WHERE userid=$1 ORDER BY timestamp ASC', [userid])
  return rows
}

const snooze = ms => new Promise(resolve => setTimeout(resolve, ms))

function makeRepeat(field, text) {
  const ref = JSON.parse(field.metadata).ref
  return { text: text,
           metadata: JSON.stringify({ repeat: true, ref  }) }
}

// BASIC OK RESPONSE
const ok = { res: 'success' }

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


  it('Recieves bailout event and switches forms',  (done) => {
    bindedDone = done.bind(this)

    const fieldsA = getFields('forms/v7R942.json')
    const fieldsB = getFields('forms/BhaV5G.json')
    const err = { error: { code: 555 }}

    testFlow = [
      [err, fieldsA[0], [makeSynthetic(userId, { type: 'bailout', value: { form: 'BhaV5G'}})]],
      [ok, fieldsB[0], []],
      [ok, fieldsB[1], []],
    ]

    sender(makeReferral(userId, 'v7R942'))
  }).timeout(20000);


  it('Test chat flow with logic jump "Yes"',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/LDfNCy.json')

    testFlow = [
      [ok, fields[0], [makePostback(fields[0], userId, 0)]],
      [ok, fields[1], [makePostback(fields[1], userId, 0)]],
      [ok, fields[2], [makeTextResponse(userId, 'LOL')]],
      [ok, fields[4], []],
      [ok, fields[5], []],
    ]

    sender(makeReferral(userId, 'LDfNCy'))

  }).timeout(20000);

  it('Test chat flow with logic jump "No"',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/LDfNCy.json')

    testFlow = [
      [ok, fields[0], [makePostback(fields[0], userId, 0)]],
      [ok, fields[1], [makePostback(fields[1], userId, 1)]],
      [ok, fields[3], []],
      [ok, fields[5], []],
    ];

    sender(makeReferral(userId, 'LDfNCy'));

  }).timeout(20000);


  it('Test chat flow with logic jump from previous question',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/jISElk.json')

    testFlow = [
      [ok, fields[0], [makeQR(fields[0], userId, 1)]],
      [ok, fields[1], [makeQR(fields[1], userId, 5)]],
      [ok, fields[2], [makeTextResponse(userId, 'LOL')]],
      [ok, fields[4], []],
      [ok, fields[5], []],
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
      [ok, fields[0], [makeQR(fields[0], userId, 1)]],
      [ok, fields[1], [makePostback(fields[1], userId, 0)]],
      [ok, fields[3], []],
    ]

    sender(makeReferral(userId, 'nFgfNE'))

  }).timeout(20000);

  it('Test chat flow with validation failures',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/ciX4qo.json')

    const repeatPhone = makeRepeat(fields[0], 'Sorry, please enter a valid mobile number.')
    const repeatEmail = makeRepeat(fields[1], 'Sorry, please enter a valid email address.')

    testFlow = [
      [ok, fields[0], [makeTextResponse(userId, '23345')]],
      [ok, repeatPhone, []],
      [ok, fields[0], [makeTextResponse(userId, '+918888000000')]],
      [ok, fields[1], [makeTextResponse(userId, 'foo')]],
      [ok, repeatEmail, []],
      [ok, fields[1], [makeTextResponse(userId, 'foo@gmail.com')]],
      [ok, fields[2], []]
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
      [ok, fieldsA[0], [makeTextResponse(userId, 'LOL')]],
      [ok, fieldsA[1], []],
      [ok, fieldsB[0], [makePostback(fieldsB[0], userId, 0)]],
      [ok, fieldsB[2], []],
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


  it('Test chat flow with multiple links and keepMoving tag',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/B6cIAn.json')

    testFlow = [
      [ok, fields[0], []],
      [ok, fields[1], []],
      [ok, fields[2], []]
    ]

    sender(makeReferral(userId, 'B6cIAn'))

  }).timeout(20000);


  it('Waits for external event and continues after event',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/Ep5wnS.json')

    testFlow = [
      [ok, fields[0], [makePostback(fields[0], userId, 0)]],
      [ok, fields[1], [makeSynthetic(userId, { type: 'external', value: {type: 'moviehouse:play', id: 164118668 }})]],
      [ok, fields[2], [makePostback(fields[2], userId, 0)]],
      [ok, fields[3], []]
    ]

    sender(makeReferral(userId, 'Ep5wnS'))

  }).timeout(20000);

  it('Works with multiple or clauses - india endline seed_16 bug',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/UGqDwc.json')

    const makeId = () => {
      const uid = uuid()
      const suitable = farmhash.fingerprint32('UGqDwc' + uid) % 16 === 3;
      return suitable ? uid : makeId();
    }

    userId = makeId()

    testFlow = [
      [ok, fields[0], [makeQR(fields[0], userId, 0)]],
      [ok, fields[1], []],
      [ok, fields[2], []],
      [ok, fields[3], []],
      [ok, fields[4], []],
      [ok, fields[5], []],
      [ok, fields[6], []],
      [ok, fields[22], []],
      [ok, fields[23], []],
      [ok, fields[24], []]
    ]

    sender(makeReferral(userId, 'UGqDwc'))

  }).timeout(20000);


  it('Sends timeout message response when interrupted in a timeout, then waits',  (done) => {
    bindedDone = done.bind(this)
    const fields = getFields('forms/vHXzrh.json')

    testFlow = [
      [ok, fields[0], [makeTextResponse(userId, 'LOL')]],
      [ok, { text: 'Please wait!', metadata: '{"repeat":true,"ref":"bd2b2376-d722-4b51-8e1e-c2000ce6ec55"}'}, []],
      [ok, fields[0], []],
      [ok, fields[1], [makeTextResponse(userId, 'LOL')]],
      [ok, fields[2], []],
    ]

    sender(makeReferral(userId, 'vHXzrh'))

  }).timeout(180000);



  it('Sends messages with notify token after timeout',  (done) => {
    bindedDone = done.bind(this)

    // TODO: test recipient!!!!

    const fields = getFields('forms/dbFwhd.json')

    testFlow = [
      [ok, fields[0], [makeNotify(userId, '{ "ref": "908088b3-5e9e-4b53-b746-799ac51bc758"}')]],
      [ok, fields[1], []],
      [ok, fields[2], [makePostback(fields[2], userId, 1)]],
      [ok, fields[3], []],
      [ok, fields[4], [makeQR(fields[4], userId, 1)]],
      [ok, fields[5], []],
    ]

    sender(makeReferral(userId, 'dbFwhd'))
  }).timeout(180000);


  sock.on('message', async (message) => {

    const dat = JSON.parse(message.toString())
    const msg = dat.message
    const recipient = dat.recipient

    // TODO: recipient = one_time_notif_req in case of notify
    const [res, get, gives] = testFlow[messages.length]
    sock.send(JSON.stringify(res))

    messages.push(msg)

    try {
      msg.should.eql(get)
    }
    catch (e) {
      console.log(util.inspect(msg, null, 8))
      console.log(util.inspect(get, null, 8))
      console.error(e)
      sock.close()
      throw e
    }

    await sender(makeEcho(get, userId))

    for (let giv of gives) {
      await sender(giv)
    }

    if (messages.length == testFlow.length) {
      messages = []
      bindedDone()
    }
  })

});
