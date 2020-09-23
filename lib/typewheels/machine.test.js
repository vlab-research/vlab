const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const fs = require('fs')
const _ = require('lodash')
const {parseLogJSON} = require('./utils')
const {followUpMessage}= require('@vlab-research/translate-typeform')
const {_initialState, getMessage, exec, act, apply, getState, getCurrentForm, getWatermark, makeEventMetadata} = require('./machine')
const form = JSON.parse(fs.readFileSync('mocks/sample.json'))
const { echo, tyEcho, statementEcho, repeatEcho, delivery, read, qr, text, sticker, multipleChoice, referral, USER_ID, reaction, syntheticBail, syntheticPR, optin, payloadReferral, syntheticRedo, synthetic } = require('./events.test')

const _echo = md => ({...echo, message: { ...echo.message, metadata: md.ref ? md : {ref: md} }})

describe('getWatermark', () => {
  it('should work with both marks', () => {
    getWatermark(read).should.deep.equal({ type: 'read', mark: 10})
    getWatermark(delivery).should.deep.equal({ type: 'delivery', mark: 15})
  })
  it('should return undefined if not a read or delivery message', () => {
    should.not.exist(getWatermark(echo))
  })
})


describe('makeEventMetadata', () => {
  it('should get the metadata for a simple linksniffer event', () => {
    const event = { event: { type: 'external', value: {type: 'linksniffer:click', url: 'foobar'}}}
    const md = makeEventMetadata(event)
    md.should.eql({event__linksniffer_click_url: 'foobar'})
  })

  it('should get multiple key/value pairs if they exist', () => {
    const event = { event: { type: 'external', value: {type: 'random', id: 'foo', foo: 'bar'}}}
    const md = makeEventMetadata(event)
    md.should.eql({event__random_id: 'foo', event__random_foo: 'bar'})
  })

  it('should unnest kv pairs if they exist', () => {
    const event = { event: { type: 'external', value: { type: 'payment:reloadly', success: false, error: { message: 'foobar', code: 'BAR', doublenest: { foo: 'baz' } }}}}

    const md = makeEventMetadata(event)
    md.should.eql({event__payment_reloadly_success: false,
                   event__payment_reloadly_error_message: 'foobar',
                   event__payment_reloadly_error_doublenest_foo: 'baz',
                   event__payment_reloadly_error_code: 'BAR'})
  })

  it('shoudl work with array values and key them out by index', () => {
    const event = { event: { type: 'external', value: { type: 'random', list: ['foo', 'bar']}}}

    const md = makeEventMetadata(event)
    md.should.eql({event__random_list_0: 'foo',
                   event__random_list_1: 'bar'})
  })

  it('should work with number values', () => {
    const event = { event: { type: 'external', value: {type: 'random', foo: 1234}}}
    const md = makeEventMetadata(event)
    md.should.eql({event__random_foo: 1234})
  })

  it('should work with boolean values', () => {
    const event = { event: { type: 'external', value: {type: 'random', foo: false}}}
    const md = makeEventMetadata(event)
    md.should.eql({event__random_foo: false})
  })

  it('should set null but not undefined values', () => {
    const event = { event: { type: 'external', value: {type: 'random', foo: undefined, bar: null}}}
    const md = makeEventMetadata(event)
    md.should.eql({ event__random_bar: null })
  })

  it('should return undefined if an event not properly formatted', () => {
    const event = { event: { type: 'external', value: {}}}
    const md = makeEventMetadata(event)
    should.not.exist(md)
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
    const state = getState(log)
    state.forms[0].should.equal('FOO')
  })

  it('Gets the first form with an initial payload referral', () => {
    const log = [payloadReferral]
    const state = getState(log)
    state.forms[0].should.equal('FOO')
  })

  it('Gets default form state if no form or referral', () => {
    const log = [text]
    const state = getState(log)
    state.forms[0].should.equal('fallback')
  })

  it('Gets default form state if no form or referral from sticker', () => {
    const log = [sticker]
    const state = getState(log)
    state.forms[0].should.equal('fallback')
  })

  it('Gets default form state even after repeated messages in history', () => {
    const log = [text, text, text]
    const state = getState(log)
    state.forms[0].should.equal('fallback')
  })

  it('Changes form with new referral', () => {
    const ref2 = {...referral, referral: {...referral.referral, ref: 'form.BAR'}}

    const log = [referral, text, echo, delivery, multipleChoice, ref2]
    const state = getState(log)
    state.forms[0].should.equal('FOO')
    state.forms.pop().should.equal('BAR')
  })

  it('Ignores additional referrals for the same form ', () => {
    const log = [referral, text, echo, delivery, multipleChoice, referral]
    const state = getState(log)
    state.forms.length.should.equal(1)
    state.forms.slice(-1)[0].should.equal('FOO')
  })

})

describe('getState', () => {

  it('Gets start state with empty log', () => {
    const log = []
    getState(log).state.should.equal('START')
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
    const log = [referral, text, echo]
    const state = getState(log)
    state.state.should.equal('QOUT')
    state.question.should.equal('foo')
  })

  it('Responds to postback', () => {
    const log = [referral, text, echo, multipleChoice]
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
    const log = [referral, echo, delivery, text, statementEcho ]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
  })


  it('QOUT after question repeated', () => {
    const log = [referral, echo, delivery, text, repeatEcho, echo, delivery]
    const state = getState(log)
    state.state.should.equal('QOUT')
    state.question.should.equal('foo') // should this be the case?
  })


  it('Updates the qa of the state even with falsey answers', () => {
    const echo2 = _echo('bar')

    const log = [referral, echo, {...text, message: {text: 0}}, _echo('bar'), {...text, message: {text: ''}}]
    const qa = getState(log).qa

    qa[0][0].should.equal('foo')
    qa[0][1].should.equal(0)
    qa[1][0].should.equal('bar')
    qa[1][1].should.equal('')
    qa.length.should.equal(2)
  })


  it('Updates the qa of the state with correct answers', () => {
    const echo2 = _echo('bar')

    const log = [referral, echo, delivery, text, echo2, delivery, text]

    const qa = getState(log).qa

    qa[0][0].should.equal('foo')
    qa[0][1].should.equal('foo')
    qa[1][0].should.equal('bar')
    qa[1][1].should.equal('foo')
    qa.length.should.equal(2)
  })

  it('Updates the qa of the state with repeats', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: { value:"quux",ref:"foo" }}}}
    const response2 = {...qr, message: { quick_reply: { payload: { value:"qux",ref:"foo" }}}}

    const log = [referral, echo, delivery, response, repeatEcho, echo, delivery, response2]
    const qa = getState(log).qa

    qa[0][1].should.equal('quux')
    qa[1][1].should.equal('qux')
    qa.length.should.equal(2)
  })

  it('Waits for external events when wait is present in echo metadata', () => {

    const wait = { type: 'timeout', value: '2 days' }


    const log = [referral, echo, text, _echo({wait, ref: 'bar'})]
    const state = getState(log)
    state.state.should.equal('WAIT_EXTERNAL_EVENT')
  })

  it('Responds while waiting with response and repeats', () => {

    const wait = { type: 'timeout', value: '2 days' }

    const log = [referral, echo, delivery, text, _echo({wait, ref: 'bar'}), text]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
  })


  it('Responds while waiting with response and repeats with old waitstart', () => {

    const wait = { type: 'timeout', value: '2 days' }

    const log = [referral, echo, delivery,
                 text,
                 _echo({wait, ref: 'foo'}),
                 text,
                 echo,
                 {...echo, timestamp: 10, message: {...echo.message, metadata: {wait}}}
                 ]
    const state = getState(log)
    state.state.should.equal('WAIT_EXTERNAL_EVENT')
    state.waitStart.should.equal(5)
  })


  it('Responds when it gets external events that fulfills timeout conditions', () => {
    const wait = { type: 'timeout', value: '1 hour' }

    // value should be...?
    const externalEvent = { source: 'synthetic',
                            event: { type: 'timeout', value: Date.now() + 1000*60*60 }}

    const d = Date.now()
    const log = [referral, text, {...echo, timestamp: d, message: {...echo.message, metadata: { wait }}}, externalEvent]

    const state = getState(log)
    state.state.should.equal('RESPONDING')
  })


  it('Responds when it gets external events that fulfill other conditions', () => {

    const wait = {
      op: 'or',
      vars:
      [ { type: 'timeout', value: '2 days' },
        { type: 'external', value: { type: 'moviehouse:play', id: 'foobar' } } ]
    }

    const externalEvent = { source: 'synthetic',
                            timestamp: Date.now(),
                            event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar' }}}


    const log = [referral, _echo({wait, ref: 'foo'}), externalEvent]

    const state = getState(log)
    state.state.should.equal('RESPONDING')
    state.question.should.equal('foo')

    // and stores metadata
    state.md.should.have.property('event__moviehouse_play_id', 'foobar')
    state.md.should.have.property('form', 'FOO')
  })

  it('continues to wait when it gets external events that partially fulfill conditions', () => {

    const wait = {
      op: 'and',
      vars:
      [ { type: 'timeout', value: '2 days' },
        { type: 'external', value: { type: 'moviehouse:play', id: 'foobar' } } ]
    }

    const externalEvent = { source: 'synthetic',
                            event: { type: 'external', value: { type: 'moviehouse:play', id: 'foobar' }}}

    const log = [referral, _echo({wait, ref: 'foo'}), externalEvent]

    const state = getState(log)
    state.state.should.equal('WAIT_EXTERNAL_EVENT')

    // and stores metadata
    state.md.should.have.property('event__moviehouse_play_id', 'foobar')
    state.md.should.have.property('form', 'FOO')
  })


  it('Responds when it gets multiple events that fulfill all conditions', () => {

    const wait = {
      op: 'and',
      vars:
      [ { type: 'timeout', value: '2 hours' },
        { type: 'external', value: { type: 'moviehouse:play', id: 'foobar' } } ]
    }

    const externalEventA = { source: 'synthetic',
                            event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar' }}}

    // value should be...?
    const externalEventB = { source: 'synthetic',
                             event: { type: 'timeout', value: Date.now() + 1000*60*120 }}

    const log = [referral, {...echo, timestamp: Date.now(), message: {...echo.message, metadata: {wait}}}, externalEventA, externalEventB]

    const state = getState(log)
    state.state.should.equal('RESPONDING')

    // and stores metadata
    state.md.should.have.property('event__moviehouse_play_id', 'foobar')
    state.md.should.have.property('form', 'FOO')
  })



  it('Does not add event to metadata if not waiting external event', () => {

    const externalEvent = { source: 'synthetic',
                            timestamp: Date.now(),
                            event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar' }}}


    const log = [referral, echo, text, externalEvent]
    const state = getState(log)

    state.state.should.equal('RESPONDING')
    state.md.should.not.have.property('event__moviehouse_play_id')
  })


  it('It switches forms after a form stitch message is sent, keeps metadata', () => {

    const metadata = { "type":"stitch", "stitch": {"form":"BAR"}, "ref":"foo" }
    const log = [referral, {...echo, message: {...echo.message, metadata} }]

    const oldState = getState([referral])
    const state = getState(log)
    state.state.should.equal('RESPONDING')
    state.forms[1].should.equal('BAR')
    state.md.form.should.equal('FOO')
    state.md.seed.should.equal(oldState.md.seed)
    state.md.startTime.should.not.equal(referral.timestamp)
    state.md.startTime.should.equal(echo.timestamp)
  })


  it('It switches forms after a form stitch message is sent, keeps metadata from previous events', () => {


    const wait = {type: 'external', value: { type: 'moviehouse:play', id: 'foobar' } }

    const externalEvent = { source: 'synthetic',
                            event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar' }}}

    const metadata = { "type":"stitch", "stitch": {"form":"BAR"}, "ref":"foo" }
    const log = [referral, _echo({wait, ref: 'foo'}), externalEvent, {...echo, message: {...echo.message, metadata} }]

    const oldState = getState([referral])
    const state = getState(log)
    state.state.should.equal('RESPONDING')
    state.forms[1].should.equal('BAR')
    state.md.form.should.equal('FOO')
    state.md.seed.should.equal(oldState.md.seed)
    state.md.startTime.should.not.equal(referral.timestamp)
    state.md.startTime.should.equal(echo.timestamp)

    state.md.should.have.property('event__moviehouse_play_id', 'foobar')
    state.md.should.have.property('form', 'FOO')
  })




  it('It keeps tokens when it stitches forms together', () => {
    const metadata = { "type":"stitch", "stitch": {"form":"BAR"}, "ref":"foo" }
    const log = [referral, optin, {...echo, message: {...echo.message, metadata} }]

    const state = getState(log)
    state.state.should.equal('RESPONDING')
    state.forms[1].should.equal('BAR')
    state.tokens.should.eql(['FOOBAR'])
  })

  it('It moves to next form on bailout when response never sent', () => {

    const log = [referral, echo, text, syntheticBail]
    const state = getState(log)

    state.state.should.equal('RESPONDING')
    state.forms[1].should.equal('BAR')
  })

  it('ignores a good platform response', () => {

    let log = [referral]
    let state1 = getState(log)
    let state2 = getState([...log, syntheticPR])
    state2.state.should.equal(state1.state)

    log = [referral, echo]
    state1 = getState(log)
    state2 = getState([...log, syntheticPR])
    state2.state.should.equal(state1.state)
  })

  it('gets into a blocked state when given a report with a FB error', () => {
    const report = synthetic({ type: 'machine_report', value: {error: { tag: 'FB', code: 200}}})
    const log = [referral, echo, text, report]
    const state = getState(log)
    state.state.should.equal('BLOCKED')
    state.error.code.should.equal(200)
  })

  it('gets into an error state when given a report with a different error', () => {
    const report = synthetic({ type: 'machine_report', value: {error: { tag: 'INTERNAL', code: 'FOO'}}})
    const log = [referral, echo, text, report]
    const state = getState(log)
    state.state.should.equal('ERROR')
    state.error.code.should.equal('FOO')
  })

  it('gets into a blocked state when given a bad platform response', () => {

    const pr = {...syntheticPR, event: {...syntheticPR.event, value: {response: { error: { code: 2022}}}}}
    const log = [referral, echo, text, pr]
    const state = getState(log)

    state.state.should.equal('BLOCKED')
  })

  it('gets out of a blocked state if an echo follows a bad platform response', () => {
    // TODO: Is this what we want??? Race conditions???

    const pr = {...syntheticPR, event: {...syntheticPR.event, value: {response: { error: { code: 2022}}}}}
    const log = [referral, echo, text, pr, echo]
    const state = getState(log)

    state.state.should.equal('QOUT')
  })

  it('gets out of a blocked state if a user responds', () => {
    // TODO: Is this what we want???
    const pr = {...syntheticPR, event: {...syntheticPR.event, value: {response: { error: { code: 2022}}}}}
    const log = [referral, echo, text, pr, text]
    const state = getState(log)

    state.state.should.equal('RESPONDING')
    state.question.should.equal('foo')
  })

  it('adds tokens to the state from an optin event', () => {

    // TODO: Is this what we want???
    const log = [referral, echo, optin]
    const state = getState(log)

    state.state.should.equal('RESPONDING')
    state.tokens.should.eql(['FOOBAR'])
    state.question.should.equal('foo')
  })

  it('removes tokens to the state when it needs to use them ', () => {
    const wait = { type: 'timeout', value: '25 hours' }

    // value should be...?
    const externalEvent = { source: 'synthetic',
                            timestamp: Date.now() + 1000*60*60*25,
                            event: { type: 'timeout', value: Date.now() + 1000*60*60*25 }}

    const d = Date.now()

    const log = [referral, optin, text, {...echo, timestamp: d, message: {...echo.message, metadata: { wait }}}, externalEvent]

    const state = getState(log)
    state.state.should.equal('RESPONDING')
    state.tokens.should.eql([])
  })
})


describe('Machine', () => {
  let user = { id: '123' }

  it('gets the correct start field even with no referral', () => {
    const output = exec(_initialState(), text)
    const action = act({user, form, log:[text]}, _initialState(), output)[0]
    action.message.attachment.payload.text.should.equal(form.fields[0].title)
  })

  it('sends the first message when it gets a referral', () => {
    const output = exec(_initialState(), referral)
    const action = act({user, form, log:[referral]}, _initialState(), output)[0]
    action.message.attachment.payload.text.should.equal(form.fields[0].title)
  })

  it('Validates answers via postback', () => {
    const form = { logic: [],
                   fields: [{type: 'legal', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, multipleChoice]
    const action = getMessage(log, form, user)[0]
    action.message.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })

  it('Invalidates answers to legal when not in set', () => {
    const form = { logic: [],
                   fields: [{type: 'legal', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form, user)[0]
    JSON.parse(action.message.metadata).repeat.should.be.true
  })


  it('Invalidates answers to short_text when a previous postback is sent', () => {
    const form = { logic: [],
                   fields: [{type: 'legal', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'},
                            {type: 'thankyou_screen', title: 'baz', ref: 'baz'}]}

    const log = [referral, echo, multipleChoice, _echo('bar'), multipleChoice]
    const action = getMessage(log, form, user)[0]
    JSON.parse(action.message.metadata).repeat.should.be.true
  })

  it('Works when initial messages are delivery', () => {
    const log = [delivery, delivery, echo]
    const state = getState(log.slice(0,-1))
    const output = exec(state, parseLogJSON([echo])[0])
    output.action.should.equal('WAIT_RESPONSE')
    output.question.should.equal('foo')
  })


  it('Validates answers via qr', () => {
    const log = [referral, text, echo, delivery, qr]
    const state = getState(log.slice(0,-1))
    const output = exec(state, qr)
    should.not.exist(output.validation)
  })

  it('It switches forms on bailout when response never sent', () => {

    const log = [referral, echo, text]
    const state = getState(log)
    const output = exec(state, syntheticBail)

    output.action.should.equal('SWITCH_FORM')
    output.form.should.equal('BAR')
    output.md.seed.should.equal(state.md.seed)
    output.md.startTime.should.not.equal(state.md.startTime)
    output.md.startTime.should.equal(syntheticBail.timestamp)
  })

  it('It ignores platform response errors when in blocked state', () => {
    const report = synthetic({ type: 'platform_response', value: {response: {error: { tag: 'FB', code: 200}}}})
    const log = [referral, echo, text, report]
    const state = getState(log)
    const output = exec(state, report)
    output.action.should.equal('NONE')
  })

  it('It ignores machine report errors when in blocked state', () => {
    const report = synthetic({ type: 'machine_report', value: {error: { tag: 'FB', code: 200}}})
    const log = [referral, echo, text, report]
    const state = getState(log)
    const output = exec(state, report)
    output.action.should.equal('NONE')
  })

  it('It ignores machine report errors when in error state', () => {
    const report = synthetic({ type: 'machine_report', value: {error: { tag: 'INTERNAL', code: 200}}})
    const log = [referral, echo, text, report]
    const state = getState(log)
    const output = exec(state, report)
    output.action.should.equal('NONE')
  })

  it('It ignores machine reports for error when in blocked state', () => {
    const report = synthetic({ type: 'machine_report', value: {error: { tag: 'FB', code: 200}}})
    const report2 = synthetic({ type: 'machine_report', value: {error: { tag: 'INTERNAL', code: 200}}})
    const log = [referral, echo, text, report]
    const state = getState(log)
    state.state.should.equal('BLOCKED')
    const output = exec(state, report2)
    output.action.should.equal('NONE')
  })

  it('It can move from a blocked state to an error state after a redo event', () => {
    const report = synthetic({ type: 'machine_report', value: {error: { tag: 'FB', code: 200}}})
    const report2 = synthetic({ type: 'machine_report', value: {error: { tag: 'INTERNAL', code: 200}}})
    const log = [referral, echo, text, report, synthetic({type: 'redo'})]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
    const output = exec(state, report2)
    output.action.should.equal('ERROR')
  })


  it('previousOutput has followUp prop when given follow_up event', () => {
    const fu = synthetic({ type: 'follow_up', value: 'foo'})
    const log = [referral, echo, fu]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
    state.previousOutput.followUp.should.be.true
  })


  it('previousOutput has no followUp prop when user continue after follow_up event', () => {
    const fu = synthetic({ type: 'follow_up', value: 'foo'})
    const log = [referral, echo, fu, echo, text, echo]
    const state = getState(log)
    state.state.should.equal('QOUT')
    should.not.exist(state.previousOutput.followUp)
  })

  it('it gets the next question when there is a next', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form, user)[0]
    action.message.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })

  it('Responds to opening text without referral', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'qux', ref: 'qux'}]}

    const log = [text]
    const actions = getMessage(log, form, user)
    actions.length.should.equal(2)
    actions.forEach((a,i) => a.message.text.should.equal(form.fields[i].title))
  })

  it('Keeps metadata from opening form switch', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: '{{hidden:foo}}', ref: 'qux'}]}

    const log = [referral, echo, text]
    const actions = getMessage(log, form, user)
    actions.length.should.equal(1)
    actions[0].message.text.should.equal('bar')
  })

  it('Responds to opening sticker without referral', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'qux', ref: 'qux'}]}

    const log = [text]
    const actions = getMessage(log, form, user)
    actions.length.should.equal(2)
    actions.forEach((a,i) => a.message.text.should.equal(form.fields[i].title))
  })

  it('Sends multiple questions if first is statement', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'statement', title: 'baz', ref: 'baz'},
                            {type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'qux', ref: 'qux'}]}

    const log = [referral]
    const actions = getMessage(log, form, user)
    actions.length.should.equal(3)
    actions.forEach((a,i) => a.message.text.should.equal(form.fields[i].title))
  })

  it('Sends multiple questions if first is moveOn', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar', properties: { description: 'type: webview\nurl: foo.com\nbuttonText: WTF\nkeepMoving: true'}},
                            {type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'qux', ref: 'qux'}]}

    const log = [referral]
    const actions = getMessage(log, form, user)
    actions.length.should.equal(2)
    actions[0].message.attachment.payload.buttons[0].url.should.equal('foo.com')
    actions[1].message.text.should.equal('foo')
  })

  it('Ignores responses to a statement if it is moving on to another question', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'short_text', title: 'foo', ref: 'foo'}]}

    const log = [referral, statementEcho, delivery, text]
    const action = getMessage(log, form, user)[0]
    should.not.exist(action)
  })

  it('Responds to 0 as a text input', () => {
    const form = { logic: [],
                   fields: [{type: 'number', title: 'foo', ref: 'foo'},
                            {type: 'statement', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, {...text, message: {text: 0}}]
    const action = getMessage(log, form, user)[0]
    action.message.text.should.equal('bar')
  })


  it('Does not resend a statement at the end', () => {
    const echo2 = {...statementEcho, message: { ...statementEcho.message, metadata: { ref: "foo", type: "statement"}}}

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'statement', title: 'foo', ref: 'foo'}]}

    const log = [referral, statementEcho, delivery, echo2]
    const action = getMessage(log, form, user)[0]
    should.not.exist(action)
  })

  it('Sends a repeat message after an answer to a statement in the end', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'thankyou_screen', title: 'baz', ref: 'baz'}]}

    const log = [referral, tyEcho, delivery, text]
    const action = getMessage(log, form, user)[0]
    JSON.parse(action.message.metadata).repeat.should.be.true
  })

  it('Responds to is_echos that come after the delivery watermark', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'thankyou_screen', title: 'baz', ref: 'baz'}]}


    const log = [referral, delivery, {...echo, timestamp: delivery.delivery.watermark}, text]
    const action = getMessage(log, form, user)[0]
    action.message.text.should.equal('baz')
  })

  it('Responds to is_echos that come before the delivery watermark', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'thankyou_screen', title: 'baz', ref: 'baz'}]}


    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form, user)[0]
    action.message.text.should.equal('baz')
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

    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form, user)[0]
    action.message.should.deep.equal({ text: 'baz', metadata: '{"ref":"baz"}' })
  })

  it('it follows logic jumps from postbacks', () => {
    const logic = { type: 'field',
                    ref: 'foo',
                    actions: [ { action: 'jump',
                                 details:
                                 { to: { type: 'field', value: 'baz' }},
                                 condition:
                                 { op: 'is',
                                   vars: [ { type: 'field', value: 'foo' },

                                           // TODO: make sure this is a reasonable test.
                                           // boolean shouldnt be possible from typeform...
                                           { type: 'constant', value: true }]}}]}

    const form = { logic: [ logic ],
                   fields: [{ type: 'legal', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'},
                            {type: 'number', title: 'baz', ref: 'baz'}]}

    const log = [referral, echo, multipleChoice]
    const action = getMessage(log, form, user)[0]
    action.message.should.deep.equal({ text: 'baz', metadata: '{"ref":"baz"}' })
  })


  it('it follows logic jumps based on event data', () => {
    const logic = { type: 'field',
                    ref: 'bar',
                    actions: [ { action: 'jump',
                                 details:
                                 { to: { type: 'field', value: 'qux' }},
                                 condition:
                                 { op: 'equal',
                                   vars: [ { type: 'hidden', value: 'event__payment_reloadly_success' },
                                           { type: 'constant', value: 'true' }]}}]}

    const form = { logic: [ logic ],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nwait:\n    type: external\n    value:\n      type: payment:reloadly'}},
                            {type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'number', title: 'baz', ref: 'baz'},
                            {type: 'number', title: 'qux', ref: 'qux'}]}


    const event = synthetic({type: 'external', value: { type: 'payment:reloadly', success: true}}) // deal with bool

    const log = [referral, _echo({ref: 'foo', type: 'wait', wait: { type: 'external', value: { type: 'payment:reloadly'}}}), event]

    const action = getMessage(log, form, user)[1]
    action.message.should.deep.equal({ text: 'qux', metadata: '{"ref":"qux"}' })
  })

  it('repeats when it misses validation', () => {

    // TODO: this is not unit test, implicitly testing validation of multiple choice.
    // fix this by injecting mock!
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'qux'}, {label: 'quux'}]}}]}

    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form, user)[0]

    // repeat ref foo with sorry message...
    action.message.metadata.should.equal('{"repeat":true,"ref":"foo"}')
    action.message.text.should.contain('Sorry')
  })

  it('uses custom_messages when they exist', () => {

    // TODO: this is not unit test, implicitly testing validation of multiple choice.
    // fix this by injecting mock!
    const form = { logic: [],
                   custom_messages: {'label.error.mustSelect': 'baz error'},
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'qux'}, {label: 'quux'}]}}]}

    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form, user)[0]

    // repeat ref foo with sorry message...
    action.message.metadata.should.equal('{"repeat":true,"ref":"foo"}')
    action.message.text.should.equal('baz error')
  })


  it('uses custom_messages when they exist', () => {

    // TODO: this is not unit test, implicitly testing validation of multiple choice.
    // fix this by injecting mock!
    const form = { logic: [],
                   custom_messages: {'label.error.mustSelect': 'baz error'},
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'qux'}, {label: 'quux'}]}}]}

    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form, user)[0]

    // repeat ref foo with sorry message...
    action.message.metadata.should.equal('{"repeat":true,"ref":"foo"}')
    action.message.text.should.equal('baz error')
  })

  it('If a wait is a statement, it does not send multiple items', () => {

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nwait:\n    type: timeout\n    value: 1 minute'}},
                           {type: 'short_text', title: 'bar', ref: 'bar' }]}

    const wait = { type: 'timeout', value: '1 minute', response: 'baz' }
    const log = [referral]

    const action = getMessage(log, form, user)
    action.length.should.equal(1)
  })

  it('repeats with custom response when responding to a wait ', () => {

    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nresponseMessage: baz\nwait:\n    type: timeout\n    value: 1 minute'}},
                           {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, text]

    const actions = getMessage(log, form, user)
    actions.length.should.equal(2)

    // repeat ref foo with sorry message...
    actions[0].message.metadata.should.equal('{"repeat":true,"ref":"foo"}')
    actions[0].message.text.should.contain('baz')
    actions[1].message.text.should.contain('foo')
  })

  it('repeats with default response when responding to a wait without response', () => {

    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nwait:\n    type: timeout\n    value: 1 minute'}},
                           {type: 'short_text', title: 'bar', ref: 'bar'}]}



    const log = [referral, echo, text]

    const actions = getMessage(log, form, user)

    actions.length.should.equal(2)

    // repeat ref foo with sorry message...
    actions[0].message.metadata.should.equal('{"repeat":true,"ref":"foo"}')
    actions[0].message.text.should.contain('No response is necessary')
    actions[1].message.text.should.contain('foo')
  })

  it('sends the messages to the token if a token is needed', () => {
    const wait = { type: 'timeout', value: '25 hours' }

    // value should be...?
    const externalEvent = { source: 'synthetic',
                            timestamp: Date.now() + 1000*60*60*25,
                            event: { type: 'timeout', value: Date.now() + 1000*60*60*25 }}

    const d = Date.now()

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nwait:\n    type: timeout\n    value: 25 hours'}},
                           {type: 'short_text', title: 'bar', ref: 'bar' }]}


    const log = [referral, optin, {...echo, timestamp: d, message: {...echo.message, metadata: { wait, ref: 'foo' }}}, externalEvent]

    const action = getMessage(log, form, user)
    action.length.should.equal(1)
    action[0].recipient.one_time_notif_token.should.equal('FOOBAR')
    action[0].message.text.should.equal('bar')
  })

  it('It creates a stitch type message when provided type stitch metadata', () => {

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties:
                             { description: 'type: stitch\nstitch:\n    form: BAR'}}]}

    const log = [referral]
    const action = getMessage(log, form, user)[0]
    JSON.parse(action.message.metadata)['type'].should.equal('stitch')
    JSON.parse(action.message.metadata)['stitch']['form'].should.equal('BAR')
  })



  it('It recieves payload referrals and starts chatting', () => {

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo'}]}

    const log = [payloadReferral]
    const action = getMessage(log, form, user)[0]

    action.message.text.should.equal('foo')
  })


  it('moves onward when validation succeeds', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, text]

    const action = getMessage(log, form, user)[0]
    action.message.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })


  it('ignores referral sent when responding', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    should.not.exist(getMessage([referral, referral], form, user)[0])
    should.not.exist(getMessage([referral, delivery, echo, text, referral], form, user)[0])
  })


  it('ignores referral sent when waiting', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nwait:\n    type: timeout\n    value: 1 minute'}},
                           {type: 'short_text', title: 'bar', ref: 'bar' }]}

    const wait = { type: 'timeout', value: '1 minute'}
    const log = [referral, {...echo, message: {...echo.message, metadata: { wait, ref: 'foo' }}}, referral]

    should.not.exist(getMessage(log, form, user)[0])
  })


  it('repeats questions on a repeat referral if unanswered question', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const messages = getMessage([referral, delivery, echo, referral], form, user)
    JSON.parse(messages[0].message.metadata).repeat.should.be.true
    messages[1].message.text.should.equal('foo')
  })

  it('ignores referrals when the person is the referrer ', () => {

    const secondRef = {...referral, referral: {... referral.referral,
                                               ref: `form.BAR.referrer.${USER_ID}`}}
    should.not.exist(getMessage([referral, echo, secondRef], form)[0])
  })

  it('ignores reactions', () => {
    should.not.exist(getMessage([referral, delivery, echo, reaction], form)[0])
  })

  it('ignores multiple responses to a single question', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}
    const log = [referral, delivery, echo, qr, qr]
    const action = getMessage(log, form, user)[0]
    should.not.exist(action)
  })


  it('Validates a quick reply when valid', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: { value:"quux",ref:"foo" }}}}
    const log = [referral, echo, delivery, response]
    const action = getMessage(log, form, user)[0]
    action.message.text.should.equal('bar')
  })

  it('Validates a quick reply with 0 value', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: '0'}, {label: '1'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: { value:0, ref:"foo" }}}}
    const log = [referral, echo, delivery, response]
    const action = getMessage(log, form, user)[0]
    action.message.text.should.equal('bar')
  })

  it('Validates a quick reply when payload is string (as in email)', () => {
    const form = { logic: [],
                   fields: [{type: 'email', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: "foo@gmail.com" }}}
    const log = [referral, echo, delivery, response]
    const action = getMessage(log, form, user)[0]
    action.message.text.should.equal('bar')
  })


  it('Invalidates a quick reply when invalid', () => {
    const del1 = {...delivery, delivery: { watermark: 5 }}

    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: { value:"qux", ref:"foo" }}}}

    const log = [referral, del1, echo, delivery, response]

    const action = getMessage(log, form, user)[0]
    JSON.parse(action.message.metadata).repeat.should.be.true
  })


  it('Validates an optin when it is a response to a notify request', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties:
                             { description: 'type: notify' }},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}


    const log = [referral, echo, optin]

    const action = getMessage(log, form, user)[0]
    action.message.text.should.equal('bar')
  })

  it('Invalidates an optin when it comes from nowhere', () => {

    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'bar', ref: 'bar'}]}


    const log = [referral, _echo('bar'), optin]

    const action = getMessage(log, form, user)[0]
    JSON.parse(action.message.metadata).repeat.should.be.true
  })


  it('Resends a message with a follow_up event', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'}]}

    const fu = synthetic({ type: 'follow_up', value: 'foo'})
    const log = [referral, echo, fu]

    const actions = getMessage(log, form, user)
    actions.length.should.equal(2)
    actions[0].message.text.should.equal(followUpMessage({}))
    actions[1].message.text.should.equal('foo')
  })


  it('ignores a follow_up event if not in QOUT state', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'}]}

    const fu = synthetic({ type: 'follow_up', value: 'foo'})
    const log = [referral, echo, text, fu]

    const actions = getMessage(log, form, user)
    actions.length.should.equal(0)
  })


  it('ignores a follow_up event for a different question', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const fu = synthetic({ type: 'follow_up', value: 'foo'})
    const log = [referral, _echo('foo'), text, _echo('bar'), fu]

    const actions = getMessage(log, form, user)
    actions.length.should.equal(0)
  })

  it('Resends a waiting message with a redo event', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, syntheticRedo]
    const actions = getMessage(log, form, user)
    actions[0].message.text.should.equal('foo')
    actions[1].message.text.should.equal('bar')
  })


  // NOTE: this isn't great from UX standpoint, but splitting up batch messages is
  // hard and rare edge case really...
  it('Resends all messages if some of a batch didnt get sent, when given a redo event', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, statementEcho, syntheticRedo]

    const actions = getMessage(log, form, user)
    actions[0].message.text.should.equal('foo')
    actions[1].message.text.should.equal('bar')
  })


  it('Redo event resends the same token if redo sent after wait time', () => {
    const wait = { type: 'timeout', value: '25 hours' }

  //   // value should be...?
    const externalEvent = { source: 'synthetic',
                            timestamp: Date.now() + 1000*60*60*25,
                            event: { type: 'timeout', value: Date.now() + 1000*60*60*25 }}

    const d = Date.now()

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nwait:\n    type: timeout\n    value: 25 hours'}},
                           {type: 'short_text', title: 'bar', ref: 'bar' }]}

    const log = [referral, optin, _echo({wait, ref: 'foo'}), externalEvent, syntheticRedo]

    const action = getMessage(log, form, user)

    action.length.should.equal(1)
    action[0].recipient.one_time_notif_token.should.equal('FOOBAR')
    action[0].message.text.should.equal('bar')
  })


  it('repeats again when redo sent on missed validation', () => {

    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'qux'}, {label: 'quux'}]}}]}

    const log = [referral, echo, text, syntheticRedo]
    const action = getMessage(log, form, user)[0]

    action.message.metadata.should.equal('{"repeat":true,"ref":"foo"}')
    action.message.text.should.contain('Sorry')
  })


  it('It switches forms again if redo sent after form switch', () => {
    const metadata = { "type":"stitch", "stitch": {"form":"BAR"}, "ref":"foo" }
    const log = [referral, _echo(metadata), syntheticRedo]

    const state = getState(log)
    state.state.should.equal('RESPONDING')
    state.forms[1].should.equal('BAR')
    state.md.form.should.equal('FOO')
  })


  it('It re-creates stitch type message when redo comes after stitch', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const metadata = { "type":"stitch", "stitch": {"form":"BAR"}, "ref":"foo" }
    const log = [referral, _echo(metadata), syntheticRedo]

    const actions = getMessage(log, form, user)
    actions.length.should.equal(2)
    actions[0].message.text.should.equal('foo')
    actions[1].message.text.should.equal('bar')
  })


  it('It redoes when blocked as reported in platform response and gets redo event', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const pr = _.set(syntheticPR, 'event.value.response', {error: {code: 2022}})
    const log = [referral, echo, pr, syntheticRedo]

    const actions = getMessage(log, form, user)
    actions.length.should.equal(2)
    actions[0].message.text.should.equal('foo')
    actions[1].message.text.should.equal('bar')
  })



  // NOTE: is this a good thing? Implies that we consider everything
  // after "echo" from Facebook a 100% sure thing... which it surely isn't...
  // but, we should do fine if user responds...
  it('ignores a redo event if the echo was recieved from facebook', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const echoBar = _.set(echo, 'message.metadata.ref', 'bar')

    const log = [referral, statementEcho, echoBar, syntheticRedo]
    const action = getMessage(log, form, user)[0]

    should.not.exist(action)
  })

})
