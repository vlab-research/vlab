require('chai').should()
var parallel = require('mocha.parallel');
const sender = require('./sender.js')
const {makeQR, makePostback, makeTextResponse, makeReferral, makeSynthetic, getFields, makeNotify} = require('@vlab-research/mox')
const uuid = require('uuid');
const farmhash = require('farmhash');
const {seed, getUserId} = require('./seed-db');
const {flowMaster} = require('./socket');
const {snooze} = require('./utils')
const {getResponses, getState} = require('./responses')
const mustache = require('mustache')
const fs = require('fs')

///////////////////////////////////////////////
// SETUP -----------------------------------
const Chatbase = require(process.env.CHATBASE_BACKEND)
const chatbase = new Chatbase()

function makeRepeat(field, text) {
  const ref = JSON.parse(field.metadata).ref
  return { text: text,
           metadata: JSON.stringify({ repeat: true, ref  }) }
}
const ok = { res: 'success' }

function interpolate(str, values) {
  return mustache.parse(str)
    .map(t => t[0] === 'name' ? values[t[1]] : t[1])
    .join('')
}


///////////////////////////////////////////////
// TESTS -----------------------------------
describe('Test Bot flow Survey Integration Testing', () => {

  before(async () => {
    await seed(chatbase)
    console.log('Test starting!')
  });

  after(() => {
    console.log('Test finished!')
  });

  parallel('Basic Functionality', function () {
    this.timeout(45000);

    it('Recieves bailout event and switches forms',  async () => {
      const userId = uuid()
      const fieldsA = getFields('forms/v7R942.json')
      const fieldsB = getFields('forms/BhaV5G.json')
      const err = { error: { code: 555 }}

      const testFlow = [
        [err, fieldsA[0], [makeSynthetic(userId, { type: 'bailout', value: { form: 'BhaV5G'}})]],
        [ok, fieldsB[0], []],
        [ok, fieldsB[1], []],
      ]

      await sender(makeReferral(userId, 'v7R942'))
      await flowMaster(userId, testFlow)
    })


    it('Follows logic jumps based on external events: payment success',  async () => {
      const userId = uuid()
      const fields = getFields('forms/SNomCIYT.json')

      const testFlow = [
        [ok, fields[0], [makeTextResponse(userId, '+918888000000')]],
        [ok, fields[1], [makeQR(fields[1], userId, 0)]],
        [ok, fields[2], []],
        [ok, fields[5], []],
      ]

      sender(makeReferral(userId, 'SNomCIYT'))
      await flowMaster(userId, testFlow)
    })

    it('Follows logic jumps based on external events: payment failure',  async () => {
      const userId = uuid()
      const vals = {'hidden:event__payment_fake_error_message': 'you fake'}
      const form = fs.readFileSync('forms/gk3gt9ag.json', 'utf-8')
      const f = interpolate(form, vals)
      fs.writeFileSync('forms/temp.json', f)

      const fields = getFields('forms/temp.json')

      const testFlow = [
        [ok, fields[0], [makeTextResponse(userId, '+918888000000')]],
        [ok, fields[1], [makeQR(fields[1], userId, 0)]],
        [ok, fields[2], []],
        [ok, fields[3], []],
        [ok, fields[4], []],
        [ok, fields[0], []],
      ]

      sender(makeReferral(userId, 'gk3gt9ag'))
      await flowMaster(userId, testFlow)
    })


    it('Test chat flow with logic jump "Yes"',  async () => {
      const userId = uuid()
      const fields = getFields('forms/LDfNCy.json')

      const testFlow = [
        [ok, fields[0], [makePostback(fields[0], userId, 0)]],
        [ok, fields[1], [makePostback(fields[1], userId, 0)]],
        [ok, fields[2], [makeTextResponse(userId, 'LOL')]],
        [ok, fields[4], []],
        [ok, fields[5], []],
      ]

      sender(makeReferral(userId, 'LDfNCy'))
      await flowMaster(userId, testFlow)
    })

    it('Test chat flow with logic jump "No"',  async () => {
      const userId = uuid()
      const fields = getFields('forms/LDfNCy.json')

      const testFlow = [
        [ok, fields[0], [makePostback(fields[0], userId, 0)]],
        [ok, fields[1], [makePostback(fields[1], userId, 1)]],
        [ok, fields[3], []],
        [ok, fields[5], []],
      ];

      sender(makeReferral(userId, 'LDfNCy'));
      await flowMaster(userId, testFlow)
    })


    it('Puts user into blocked state when given facebook error',  async () => {
      const userId = uuid()
      const fields = getFields('forms/LDfNCy.json')
      const err = { error: { code: 555 }}

      const testFlow = [
        [err, fields[0], []]
      ]

      sender(makeReferral(userId, 'LDfNCy'))
      await flowMaster(userId, testFlow)

      // wait for scribble to catch up
      await snooze(8000)
      const state = await getState(chatbase, userId)
      state.current_state.should.equal('BLOCKED')
      state.fb_error_code.should.equal('555')
    })

    it('Puts user into error state when given a bad form',  async () => {
      const userId = uuid()
      sender(makeReferral(userId, 'DOESNTEXIST'))

      // wait for scribble to catch up
      await snooze(8000)
      const state = await getState(chatbase, userId)
      state.current_state.should.equal('ERROR')
      state.state_json.error.tag.should.equal('INTERNAL')
      state.state_json.error.message.should.equal('getForm')
      state.state_json.error.status.should.equal(404)
    })


    it('Test chat flow with logic jump from previous question',  async () => {
      const userId = uuid()
      const fields = getFields('forms/jISElk.json')

      const testFlow = [
        [ok, fields[0], [makeQR(fields[0], userId, 1)]],
        [ok, fields[1], [makeQR(fields[1], userId, 5)]],
        [ok, fields[2], [makeTextResponse(userId, 'LOL')]],
        [ok, fields[4], []],
        [ok, fields[5], []],
      ]

      sender(makeReferral(userId, 'jISElk'))
      await flowMaster(userId, testFlow)

    })

    it('Test chat flow logic jump from hidden seed_2 field', async () => {
      const fields = getFields('forms/nFgfNE.json')

      const makeId = () => {
        const uid = uuid()
        const suitable = farmhash.fingerprint32('nFgfNE' + uid) % 2 === 0;
        return suitable ? uid : makeId();
      }

      const userId = makeId()

      const testFlow = [
        [ok, fields[0], [makeQR(fields[0], userId, 1)]],
        [ok, fields[1], [makePostback(fields[1], userId, 0)]],
        [ok, fields[3], []],
      ]

      sender(makeReferral(userId, 'nFgfNE'))
      await flowMaster(userId, testFlow)

    })

    it('Test chat flow with validation failures',  async () => {
      const userId = uuid()
      const fields = getFields('forms/ciX4qo.json')

      const repeatPhone = makeRepeat(fields[0], 'Sorry, please enter a valid phone number.')
      const repeatEmail = makeRepeat(fields[1], 'Sorry, please enter a valid email address.')

      const testFlow = [
        [ok, fields[0], [makeTextResponse(userId, '23345')]],
        [ok, repeatPhone, []],
        [ok, fields[0], [makeTextResponse(userId, '+918888000000')]],
        [ok, fields[1], [makeTextResponse(userId, 'foo')]],
        [ok, repeatEmail, []],
        [ok, fields[1], [makeTextResponse(userId, 'foo@gmail.com')]],
        [ok, fields[2], []]
      ];

      sender(makeReferral(userId, 'ciX4qo'));
      await flowMaster(userId, testFlow)
    })

    it('Test chat flow with custom validation error messages',  async () => {
      const userId = uuid()

      const fields = getFields('forms/KAvzEUWn.json')

      const repeatNumber = makeRepeat(fields[0], 'foo number bar')
      const repeatSelect = makeRepeat(fields[1], '*foo selection bar*')

      const testFlow = [
        [ok, fields[0], [makeTextResponse(userId, 'haha not number')]],
        [ok, repeatNumber, []],
        [ok, fields[0], [makeTextResponse(userId, '590')]],
        [ok, fields[1], [makeTextResponse(userId, 'foozzzz')]],
        [ok, repeatSelect, []],
        [ok, fields[1], [makeQR(fields[1], userId, 0)]],
        [ok, fields[2], []]
      ];

      sender(makeReferral(userId, 'KAvzEUWn'));
      await flowMaster(userId, testFlow)
    })

    it('Test chat flow with stitched forms: stitches and maintains seed"',  async () => {
      const makeId = () => {
        const uid = uuid()
        const suitable = farmhash.fingerprint32('Llu24B' + uid) % 5 === 0;
        return suitable ? uid : makeId();
      }

      const userId = makeId()


      const fieldsA = getFields('forms/Llu24B.json')
      const fieldsB = getFields('forms/tKG55U.json')

      const testFlow = [
        [ok, fieldsA[0], [makeTextResponse(userId, 'LOL')]],
        [ok, fieldsA[1], []],
        [ok, fieldsB[0], [makePostback(fieldsB[0], userId, 0)]],
        [ok, fieldsB[2], []],
      ]

      sender(makeReferral(userId, 'Llu24B'))
      await flowMaster(userId, testFlow)

      await snooze(8000)
      const res = await getResponses(chatbase, userId)
      res.length.should.equal(2)
      res.map(r => r['response']).should.include('LOL')
      res.map(r => r['response']).should.include('true')
      res.map(r => r['parent_shortcode']).should.eql(['Llu24B', 'Llu24B'])
    })

    it('Test chat flow on forms with translated responses',  async () => {
      const userId = uuid()
      const [source, dest] = ['hc2slBXH', 'mzs7qmvZ']

      const query = `update surveys set translation_conf = jsonb_set(translation_conf, ARRAY['destination'], to_json((select id from surveys where shortcode = $1 limit 1)::STRING)) where shortcode = $2;`

      await chatbase.pool.query(query, [dest, source])

      const fields = getFields('forms/hc2slBXH.json')

      const testFlow = [
        [ok, fields[0], [makeQR(fields[0], userId, 0)]],
        [ok, fields[1], [makeTextResponse(userId, 'LOL')]],
        [ok, fields[2], []],
      ]

      sender(makeReferral(userId, 'hc2slBXH'))
      await flowMaster(userId, testFlow)

      await snooze(8000)
      const res = await getResponses(chatbase, userId)
      res.length.should.equal(2)
      res.map(r => r['response']).should.include('LOL')
      res.map(r => r['response']).should.include('Good')
      res.map(r => r['translated_response']).should.include('LOL')
      res.map(r => r['translated_response']).should.include('Bien')
    })

    it('Test chat flow with multiple links and keepMoving tag',  async () => {
      const userId = uuid()
      const fields = getFields('forms/B6cIAn.json')

      const testFlow = [
        [ok, fields[0], []],
        [ok, fields[1], []],
        [ok, fields[2], []]
      ]

      sender(makeReferral(userId, 'B6cIAn'))
      await flowMaster(userId, testFlow)
    })


    it('Waits for external event and continues after event',  async () => {
      const userId = uuid()
      const fields = getFields('forms/Ep5wnS.json')

      const testFlow = [
        [ok, fields[0], [makePostback(fields[0], userId, 0)]],
        [ok, fields[1], [makeSynthetic(userId, { type: 'external', value: {type: 'moviehouse:play', id: 164118668 }})]],
        [ok, fields[2], [makePostback(fields[2], userId, 0)]],
        [ok, fields[3], []]
      ]

      sender(makeReferral(userId, 'Ep5wnS'))
      await flowMaster(userId, testFlow)
    })

    it('Works with multiple or clauses - india endline seed_16 bug',  async () => {
      const fields = getFields('forms/UGqDwc.json')

      const makeId = () => {
        const uid = uuid()
        const suitable = farmhash.fingerprint32('UGqDwc' + uid) % 16 === 3;
        return suitable ? uid : makeId();
      }

      const userId = makeId()

      const testFlow = [
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
      await flowMaster(userId, testFlow)
    })
  })


  parallel('Timeouts', function () {
    this.timeout(180000)

    it('Sends timeout message response when interrupted in a timeout, then waits',  async () => {
      const userId = uuid()
      const fields = getFields('forms/vHXzrh.json')

      const testFlow = [
        [ok, fields[0], [makeTextResponse(userId, 'LOL')]],
        [ok, { text: 'Please wait!', metadata: '{"repeat":true,"ref":"bd2b2376-d722-4b51-8e1e-c2000ce6ec55"}'}, []],
        [ok, fields[0], []],
        [ok, fields[1], [makeTextResponse(userId, 'LOL')]],
        [ok, fields[2], []],
      ]

      sender(makeReferral(userId, 'vHXzrh'))
      await flowMaster(userId, testFlow)
    })


    it('Sends message after timeout absolute timeout',  async () => {
      const userId = uuid()
      const timeoutDate = (new Date(Math.floor(Date.now()/1000 + 60)*1000)).toISOString()

      const vals = {'hidden:timeout_date': timeoutDate}
      const form = fs.readFileSync('forms/j1sp7ffL.json', 'utf-8')
      const f = interpolate(form, vals)
      fs.writeFileSync('forms/temp-j1sp7ffL.json', f)

      const fields = getFields('forms/temp-j1sp7ffL.json')

      const testFlow = [
        [ok, fields[0], []],
        [ok, fields[1], [makeTextResponse(userId, 'loved it')]],
        [ok, fields[2], []],
      ]
      sender(makeReferral(userId, `j1sp7ffL.timeout_date.${timeoutDate}`))
      await flowMaster(userId, testFlow)
    })

    it('Sends messages with notify token after timeout',  async () => {
      const userId = uuid()

      const fields = getFields('forms/dbFwhd.json')

      const testFlow = [
        [ok, fields[0], [makeNotify(userId, '{ "ref": "908088b3-5e9e-4b53-b746-799ac51bc758"}')]],
        [ok, fields[1], []],
        [ok, fields[2], [makePostback(fields[2], userId, 1)]],
        [ok, fields[3], []],
        [ok, fields[4], [makeQR(fields[4], userId, 1)], 'FOOBAR'], // checks recipient is token
        [ok, fields[5], []],
      ]

      sender(makeReferral(userId, 'dbFwhd'))
      await flowMaster(userId, testFlow)
    })


    it('Sends follow ups when the user does not respond',  async () => {
      const userId = uuid()
      const fields = getFields('forms/ulrtpfSQ.json')

      const followUp = makeRepeat(fields[0], 'this is a follow up')

      const testFlow = [
        [ok, fields[0], []],
        [ok, followUp, []],
        [ok, fields[0], [makeQR(fields[0], userId, 0)]],
        [ok, fields[1], []],
      ]

      sender(makeReferral(userId, 'ulrtpfSQ'))
      await flowMaster(userId, testFlow)
    })
  })

});
