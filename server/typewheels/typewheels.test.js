const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const fs = require('fs')

const t = require('./typewheels')
const translator = require('typeform-to-facebook-messenger').translator

const form = JSON.parse(fs.readFileSync('mocks/sample.json'))


const { echo, statementEcho, repeatEcho, delivery, read, qr, text, multipleChoice, referral} = require('./events.test')

describe('getWatermark', () => {
  it('should work with both marks', () => {
    t.getWatermark(read).should.deep.equal({ type: 'read', mark: 10})
    t.getWatermark(delivery).should.deep.equal({ type: 'delivery', mark: 15})
  })
  it('should return undefined if not a read or delivery message', () => {
    should.not.exist(t.getWatermark(echo))
  })
})


describe('getState', () => {

  it('Throws when given empty log', () => {
    const log = []
    t.getState.bind(null, log).should.throw(TypeError)
    t.getState.bind(null).should.throw(TypeError)
  })

  it('Gets a start state at the start', () => {
    const log = [referral]
    const state = t.getState(log)
    state.should.deep.equal({ form: 'FOO', state: 'START'})
  })


  it('Gets undefined state if no form or referral', () => {
    const log = [text]
    const state = t.getState(log)
    should.not.exist(state)
  })

  it('Changes form with new referral', () => {
    const ref2 = {...referral, referral: {...referral.referral, ref: 'BAR.something'}}

    const log = [referral, text, echo, delivery, read, multipleChoice, ref2]
    const state = t.getState(log)
    state.form.should.equal('BAR')
    state.state.should.equal('START')
    should.not.exist(state.response)
  })

  it('Ignores additional referrals for the same form ', () => {
    const log = [referral, text, echo, delivery, read, multipleChoice, referral]
    const state = t.getState(log)
    state.form.should.equal('FOO')
    state.state.should.equal('QA')
  })

  it('Gets a question outstanding state delivered', () => {
    const log = [referral, text, echo, delivery]
    const state = t.getState(log)
    state.form.should.equal('FOO')
    state.state.should.equal('QOUT')
    should.not.exist(state.response)
    // state.isDelivered.should.be.true
    // state.isRead.should.be.true
  })

  it('Gets a question outstanding state read', () => {
    const log = [referral, text, echo, delivery, read]
    const state = t.getState(log)
    state.form.should.equal('FOO')
    state.state.should.equal('QOUT')
    should.not.exist(state.response)
    // state.isDelivered.should.be.true
    // state.isRead.should.be.true
  })

  it('Gets an answer via postback', () => {
    const log = [referral, text, echo, delivery, read, multipleChoice]
    const state = t.getState(log)
    state.form.should.equal('FOO')
    state.state.should.equal('QA')
    state.question.should.equal('foo')
    state.response.should.equal(true)
  })

  it('Gets an answer via quick reply', () => {
    const log = [referral, echo, qr]
    const state = t.getState(log)
    state.form.should.equal('FOO')
    state.state.should.equal('QA')
    state.question.should.equal('foo')
    state.response.should.equal('Continue')
  })

  it('Gets an answer via freetext', () => {
    const log = [referral, echo, text]
    const state = t.getState(log)
    state.form.should.equal('FOO')
    state.state.should.equal('QA')
    state.question.should.equal('foo')
    state.response.should.equal('foo')
  })

  it('Gets an answer when a statement is sent', () => {
    const log = [referral, echo, delivery, read, text, statementEcho, delivery, read]
    const state = t.getState(log)
    state.form.should.equal('FOO')
    state.state.should.equal('QA')
    state.question.should.equal('bar')
    should.not.exist(state.response)
  })


  it('Gets a repeat state after question repeated', () => {
    const log = [referral, echo, delivery, read, text, repeatEcho]
    const state = t.getState(log)
    state.form.should.equal('FOO')
    state.state.should.equal('REPEAT')
    state.question.should.equal('bar')
    should.not.exist(state.response)
  })

  it('Gets an invalid state after a postback to a previous question', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "bar"}'}}
    const log = [referral, echo2, delivery, read, multipleChoice]
    const state = t.getState(log)
    state.form.should.equal('FOO')
    state.state.should.equal('QA')
    state.question.should.equal('bar')
    state.valid.should.be.false
    should.not.exist(state.response)
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


describe('getAction', () => {
  it('Gets the first question when the state is start', () => {

  })
})

describe('Form', () => {
  it('works', () => {
    // const f = new Form()
    // console.log(form.fields.map(translator))
  })
})
