const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const fs = require('fs')

const t = require('./typewheels')

const form = JSON.parse(fs.readFileSync('mocks/sample.json'))


// if postback --> JSON.parse payload
// else if message --> get quick reply or text? Ignore quick reply? Mark if quick reply?

const referral =  {
  recipient: { id: '1051551461692797' },
  timestamp: 1542123799219,
  sender: { id: '1800244896727776' },
  referral:
   { ref: 'NANDAN.rao.hello.ok',
     source: 'SHORTLINK',
     type: 'OPEN_THREAD' } }

// multiple choice response
const multipleChoice = {
  recipient: { id: '1051551461692797' },
  timestamp: 1542116257642,
  sender: { id: '1800244896727776' },
  postback:
   { payload: '{"value":"I Accept","ref":"foo"}',
     title: 'I Accept' } }

// Continue sent by user...
const text = {
  sender: { id: '1800244896727776' },
  recipient: { id: '1051551461692797' },
  timestamp: 1542116363617,
  message: { text: 'foo' } }

// Continue via quick reply...
const qr = {
  sender: { id: '1800244896727776' },
  recipient: { id: '1051551461692797' },
  timestamp: 20,
  message:
   { quick_reply: { payload: 'Continue' },
     text: 'Continue' } }

  // read
const read =  {
  sender: { id: '1800244896727776' },
    recipient: { id: '1051551461692797' },
    timestamp: 15,
    read: {watermark: 10 } }

const delivery = {
  sender: { id: '1800244896727776' },
  recipient: { id: '1051551461692797' },
  timestamp: 16,
  delivery:
   { watermark: 15 }}


  // is echo
const echo = {
  sender: { id: '1051551461692797' },
  recipient: { id: '1800244896727776' },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: '{ "ref": "foo" }',
    text: 'Whatsupp welcome you agree or what?' } }


describe('getWatermark', () => {
  it('returns watermarks', () => {
    const log = [text, read, delivery]
    t.getWatermark('delivery', log).should.equal(15)
    t.getWatermark('read', log).should.equal(10)
  })

  it('returns watermark with multiple', () => {
    const d2 = {...delivery, delivery: {watermark: 25}}
    const log = [text, read, delivery, d2]
    t.getWatermark('delivery', log).should.equal(25)
    t.getWatermark('read', log).should.equal(10)
  })

})

describe('getLogState', () => {
  it('translates simple state', () => {
    const log = [referral, text]
    t.getLogState(log).history.should.deep.equal([])
    t.getLogState(log).form.should.equal('NANDAN')
  })

  it('updates to a new form', () => {
    const referral2 = {...referral, referral: {...referral.referral, ref: 'QUX.baz', }}
    const log = [referral, text, echo, delivery, read, multipleChoice, referral2]
    t.getLogState(log).history.should.deep.equal([])
    t.getLogState(log).form.should.equal('QUX')
  })

  it('Gets whole history of complex state', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "bar"}'}}
    const log = [referral, text, echo, delivery, read, multipleChoice, text, echo2]
    const state = t.getLogState(log)
    // state.history.map(i => i[0]).should.deep.equal(['foo', 'bar'])
  })

  it('Gets whole history of complex state when postbacks out of order', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "bar"}'}}
    // const read2 =
    const log = [referral, text, echo, delivery, read, echo2, multipleChoice, read, text]
    const state = t.getLogState(log)

    // correctly assigns multipleChoice to first echo
    state.history[0][1].length.should.equal(1)
    JSON.parse(state.history[0][1][0].postback.payload).should.deep.equal({
      value: 'I Accept',
      ref: 'foo'
    })

    // assigns second text to echo2
    state.history[1][1].length.should.equal(1)
    state.history[1][1][0].message.text.should.equal('foo')
  })

})

describe('getState', () => {
  it('Gets a simple state at the start', () => {
    const log = [referral, text]
    const state = t.getState(t.getLogState(log))
    state.should.deep.equal({ state: 'start'})
  })

  it('Gets a question outstanding state delivered', () => {
    const log = [referral, text, echo, delivery]
    const state = t.getState(t.getLogState(log))
    state.state.should.equal('qOut')
    state.isDelivered.should.be.true
    state.isRead.should.be.false
  })

  it('Gets a question outstanding state read', () => {
    const log = [referral, text, echo, delivery, read]
    const state = t.getState(t.getLogState(log))
    state.state.should.equal('qOut')
    state.isDelivered.should.be.true
    state.isRead.should.be.true
  })

  it('Gets a question answreed', () => {

    const log = [referral, text, echo, delivery, read, multipleChoice]
    const state = t.getState(t.getLogState(log))
    console.log(state)
    state.isValid.should.be.true // ??
    JSON.parse(state.question.message.metadata).ref.should.equal('foo')
    JSON.parse(state.responses[0].postback.payload).ref.should.equal('foo')
  })
})

// STATES
const qA = {
  state: 'qA',
  question: { sender: { id: 'foo'}, recipient: { id: 'bar'}, timestamp: 5, message: {}},
  responses: []
  // isValid????
}

const qOut = {
  state: 'qOut',
  question: 'foo',
  // is read? is delivered?
  outstanding: 305040
}

const start = {
  state: 'start'
}


describe('state machine', () => {

})


describe('getField', () => {
  // it('gets the field if it exists', () => {
  //   const field = '4cc5c31b-6d23-4d50-8536-7abf1cdf0782'
  //   t.getField(r,field).should.deep.equal(r.fields[0])
  // })
  // it('returns undefined otherwise', () => {
  //   const field = 'foo'
  //   should.not.exist(t.getField(r,field))
  // })
})

describe('getCondition', () => {
  it('works with always true', () => {
    const con = form.logic[2].actions[0].condition
    t.getCondition(form, con).should.be.true
  })
})
