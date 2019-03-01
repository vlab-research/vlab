const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const fs = require('fs')
const {parseLogJSON} = require('./utils')
const {getMessage, exec, act, apply, getState, getCurrentForm, getWatermark} = require('./machine')
const form = JSON.parse(fs.readFileSync('mocks/sample.json'))
const { echo, tyEcho, statementEcho, repeatEcho, delivery, read, qr, text, multipleChoice, referral} = require('./events.test')

describe('getWatermark', () => {
  it('should work with both marks', () => {
    getWatermark(read).should.deep.equal({ type: 'read', mark: 10})
    getWatermark(delivery).should.deep.equal({ type: 'delivery', mark: 15})
  })
  it('should return undefined if not a read or delivery message', () => {
    should.not.exist(getWatermark(echo))
  })
})

describe('getCurrentForm', () => {
  let prevFallback

  before(() => {
    prevFallback = process.env.FALLBACK_FORM
    process.env.FALLBACK_FORM = 'fallback'
  })
  after(() => {
    process.env.FALLBACK_FORM = prevFallback
  })

  it('Gets the first form with an initial referral', () => {
    const log = [referral]
    const [formId, currentLog] = getCurrentForm(log)
    formId.should.equal('FOO')
  })

  it('Gets default form state if no form or referral', () => {
    const log = [text]
    const [formId, currentLog] = getCurrentForm(log)
    formId.should.equal('fallback')
  })

  it('Gets default form state even after repeated messages in history', () => {
    const log = [text, text, text]
    const [formId, currentLog] = getCurrentForm(log)
    formId.should.equal('fallback')
  })

  it('Changes form with new referral', () => {
    const ref2 = {...referral, referral: {...referral.referral, ref: 'form.BAR'}}

    const log = [referral, text, echo, delivery, read, multipleChoice, ref2]
    const [formId, currentLog] = getCurrentForm(log)
    formId.should.equal('BAR')
  })


  it('Ignores additional referrals for the same form ', () => {
    const log = [referral, text, echo, delivery, read, multipleChoice, referral]
    const [formId, currentLog] = getCurrentForm(log)
    formId.should.equal('FOO')
    currentLog.length.should.equal(7)
  })

})

describe('getState', () => {

  it('Gets start state with empty log', () => {
    const log = []
    getState(log).should.deep.equal({ state: 'START' })
  })

  it('Responds to a referral', () => {
    const log = [referral]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
    should.not.exist(state.question)
  })

  it('Gets a question responding state before delivered', () => {
    const log = [referral, text ]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
    should.not.exist(state.question)
  })

  it('Gets a question responding state to unnanounced message', () => {
    const log = [ text ]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
    should.not.exist(state.question)
  })

  it('Gets a question outstanding state if delivered', () => {
    const log = [referral, text, echo ]
    const state = getState(log)
    state.state.should.equal('QOUT')
    state.question.should.equal('foo')
  })

  it('Responds to postback', () => {
    const log = [referral, text, echo, delivery, read, multipleChoice]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
  })

  it('Responds to quick reply', () => {
    const log = [referral, echo, qr]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
  })

  it('Responds to freetext', () => {
    const log = [referral, echo, text]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
  })

  it('Responds to own statements', () => {
    const log = [referral, echo, delivery, read, text, statementEcho ]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
  })


  it('QOUT after question repeated', () => {
    const log = [referral, echo, delivery, read, text, repeatEcho]
    const state = getState(log)
    state.state.should.equal('QOUT')
    state.question.should.equal('foo') // should this be the case?
  })
})


describe('Machine', () => {

  it('responds with starting question when messaged randomly', () => {
    const output = exec({ state: 'START' }, text)
    output.action.should.equal('RESPOND')
    should.not.exist(output.question)
  })

  it('gets the correct start field even with no referral', () => {
    const output = exec({ state: 'START'}, text)
    const action = act({form, log:[text]}, {state: 'START' }, output)
    action.attachment.payload.text.should.equal(form.fields[0].title)
  })

  it('sends the first message when it gets a referral', () => {
    const output = exec({ state: 'START'}, referral)
    const action = act({form, log:[referral]}, {state: 'START' }, output)
    action.attachment.payload.text.should.equal(form.fields[0].title)
  })

  it('Autovalidates answers via postback', () => {
    const log = [referral, text, echo, delivery, read, multipleChoice]
    const state = getState(log.slice(0,-1))
    const output = exec(state, multipleChoice)
    output.validation.valid.should.be.true
  })

  it('Gets an invalid state after a postback to a previous question', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "bar"}'}}
    const log = [referral, echo2, delivery, read, multipleChoice]
    const action = getMessage(log, form)
    JSON.parse(action.metadata).repeat.should.be.true
  })


  it('Works when initial messages are delivery', () => {
    const log = [delivery, read, delivery, echo]
    const state = getState(log.slice(0,-1))
    const output = exec(state, parseLogJSON([echo])[0])
    output.action.should.equal('WAIT_RESPONSE')
    output.question.should.equal('foo')
  })


  it('Validates answers via qr', () => {
    const log = [referral, text, echo, delivery, read, qr]
    const state = getState(log.slice(0,-1))
    const output = exec(state, qr)
    should.not.exist(output.validation)
  })

  it('it gets the next question when there is a next', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, read, text]
    const action = getMessage(log, form)
    action.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })

  it('Ignores responses to a statement if it is moving on to another question', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'short_text', title: 'foo', ref: 'foo'}]}

    const log = [referral, statementEcho, delivery, read, text]
    const action = getMessage(log, form)
    should.not.exist(action)
  })


  it('Does not resend a statement at the end', () => {
    const echo2 = {...statementEcho, message: { ...statementEcho.message, metadata: { ref: "foo", type: "statement"}}}

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'statement', title: 'foo', ref: 'foo'}]}

    const log = [referral, statementEcho, read, delivery, echo2]
    const action = getMessage(log, form)
    should.not.exist(action)
  })

  it('Sends a repeat message after an answer to a statement in the end', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'thankyou_screen', title: 'baz', ref: 'baz'}]}

    const log = [referral, tyEcho, delivery, read, text]
    const action = getMessage(log, form)
    JSON.parse(action.metadata).repeat.should.be.true
  })



  it('it follows logic jumps when there are some to follow', () => {
    const logic = { type: 'field',
                    ref: 'foo',
                    actions: [ { action: 'jump',
                                 details:
                                 { to: { type: 'field', value: 'baz' }},
                                 condition:
                                 { op: 'is',
                                   vars: [ { type: 'field', value: 'foo' },
                                           { type: 'constant', value: 'foo' }]}}]}

    const form = { logic: [ logic ],
                   fields: [{ type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'},
                            {type: 'number', title: 'baz', ref: 'baz'}]}

    const log = [referral, echo, delivery, read, text]
    const action = getMessage(log, form)
    action.should.deep.equal({ text: 'baz', metadata: '{"ref":"baz"}' })
  })

  it('repeats when it misses validation', () => {

    // TODO: this is not unit test, implicitly testing validation of multiple choice.
    // fix this by injecting mock!
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'qux'}, {label: 'quux'}]}}]}

    const log = [referral, echo, delivery, read, text]
    const action = getMessage(log, form)

    // repeat ref foo with sorry message...
    action.metadata.should.equal('{"repeat":true,"ref":"foo"}')
    action.text.should.contain('Sorry')
  })

  it('moves onward when validation succeeds', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, read, text]

    const action = getMessage(log, form)
    action.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })

  it('ignores multiple open events at any time', () => {
    should.not.exist(getMessage([referral, delivery, read, echo, referral], form))
    should.not.exist(getMessage([referral, delivery, read, echo, text, referral], form))
    should.not.exist(getMessage([referral, referral], form))
  })

  it('ignores multiple responses to a single question', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}
    const log = [referral, delivery, read, echo, qr, qr]
    const action = getMessage(log, form)
    should.not.exist(action)
  })


  it('Validates a quick reply when valid', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: { value:"quux",ref:"foo" }}}}
    const log = [referral, delivery, read, echo, response]
    const action = getMessage(log, form)
    action.text.should.equal('bar')
  })


  it('Invalidates a quick reply when invalid', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: { value:"qux",ref:"foo" }}}}
    const log = [referral, delivery, read, echo, response]
    const action = getMessage(log, form)
    JSON.parse(action.metadata).repeat.should.be.true
  })

})
