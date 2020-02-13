const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const fs = require('fs')
const {parseLogJSON} = require('./utils')
const {_initialState, getMessage, exec, act, apply, getState, getCurrentForm, getWatermark} = require('./machine')
const form = JSON.parse(fs.readFileSync('mocks/sample.json'))
const { echo, tyEcho, statementEcho, repeatEcho, delivery, read, qr, text, sticker, multipleChoice, referral, USER_ID, reaction} = require('./events.test')

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
    const log = [referral, text, echo, delivery]
    const state = getState(log)
    state.state.should.equal('QOUT')
    state.question.should.equal('foo')
  })

  it('Responds to postback', () => {
    const log = [referral, text, echo, delivery, multipleChoice]
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


  it('Updates the qa of the state with correct answers', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: { ref: "bar"}}}

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


    const log = [referral, echo, delivery, text, {...echo, message: {...echo.message, metadata: {wait}}}]
    const state = getState(log)
    state.state.should.equal('WAIT_EXTERNAL_EVENT')
  })

  it('Responds while waiting with response and repeats', () => {

    const wait = { type: 'timeout', value: '2 days' }

    const log = [referral, echo, delivery, text, {...echo, message: {...echo.message, metadata: {wait}}}, text]
    const state = getState(log)
    state.state.should.equal('RESPONDING')
  })


  it('Responds while waiting with response and repeats with old waitstart', () => {

    const wait = { type: 'timeout', value: '2 days' }

    const log = [referral, echo, delivery,
                 text,
                 {...echo, message: {...echo.message, metadata: {wait}}},
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


    const log = [referral, text, {...echo, message: {...echo.message, metadata: { ...echo.message.metadata, wait }}}, externalEvent]

    const state = getState(log)
    state.state.should.equal('RESPONDING')
    state.question.should.equal('foo')
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

    const log = [referral, text, {...echo, message: {...echo.message, metadata: {wait}}}, , externalEvent]

    const state = getState(log)
    state.state.should.equal('WAIT_EXTERNAL_EVENT')
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

    const log = [referral, text, {...echo, timestamp: Date.now(), message: {...echo.message, metadata: {wait}}}, externalEventA, externalEventB]

    const state = getState(log)
    state.state.should.equal('RESPONDING')
  })


  it('It switches forms after a form stitch message is sent, keeps metadata', () => {

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties:
                             { description: 'type: stitch\nstitch:\n    form: BAR'}}]}

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
})


describe('Machine', () => {
  it('gets the correct start field even with no referral', () => {
    const output = exec(_initialState(), text)
    const action = act({form, log:[text]}, _initialState(), output)[0]
    action.attachment.payload.text.should.equal(form.fields[0].title)
  })

  it('sends the first message when it gets a referral', () => {
    const output = exec(_initialState(), referral)
    const action = act({form, log:[referral]}, _initialState(), output)[0]
    action.attachment.payload.text.should.equal(form.fields[0].title)
  })

  it('Validates answers via postback', () => {
    const form = { logic: [],
                   fields: [{type: 'legal', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, multipleChoice]
    const action = getMessage(log, form)[0]
    action.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })

  it('Invalidates answers to legal when not in set', () => {
    const form = { logic: [],
                   fields: [{type: 'legal', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form)[0]
    JSON.parse(action.metadata).repeat.should.be.true
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

  it('it gets the next question when there is a next', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form)[0]
    action.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })


  it('Responds to opening text without referral', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'qux', ref: 'qux'}]}

    const log = [text]
    const actions = getMessage(log, form)
    actions.length.should.equal(2)
    actions.forEach((a,i) => a.text.should.equal(form.fields[i].title))
  })

  it('Keeps metadata from opening form switch', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: '{{hidden:foo}}', ref: 'qux'}]}

    const log = [referral, echo, text]
    const actions = getMessage(log, form)
    actions.length.should.equal(1)
    actions[0].text.should.equal('bar')
  })

  it('Responds to opening sticker without referral', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'qux', ref: 'qux'}]}

    const log = [text]
    const actions = getMessage(log, form)
    actions.length.should.equal(2)
    actions.forEach((a,i) => a.text.should.equal(form.fields[i].title))
  })

  it('Sends multiple questions if first is statement', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'statement', title: 'baz', ref: 'baz'},
                            {type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'qux', ref: 'qux'}]}

    const log = [referral]
    const actions = getMessage(log, form)
    actions.length.should.equal(3)
    actions.forEach((a,i) => a.text.should.equal(form.fields[i].title))
  })

  it('Sends multiple questions if first is moveOn', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar', properties: { description: 'type: webview\nurl: foo.com\nbuttonText: WTF\nkeepMoving: true'}},
                            {type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'qux', ref: 'qux'}]}

    const log = [referral]
    const actions = getMessage(log, form)
    actions.length.should.equal(2)
    actions[0].attachment.payload.buttons[0].url.should.equal('foo.com')
    actions[1].text.should.equal('foo')
  })

  it('Ignores responses to a statement if it is moving on to another question', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'short_text', title: 'foo', ref: 'foo'}]}

    const log = [referral, statementEcho, delivery, text]
    const action = getMessage(log, form)[0]
    should.not.exist(action)
  })

  it('Responds to 0 as a text input', () => {
    const form = { logic: [],
                   fields: [{type: 'number', title: 'foo', ref: 'foo'},
                            {type: 'statement', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, {...text, message: {text: 0}}]
    const action = getMessage(log, form)[0]
    action.text.should.equal('bar')
  })


  it('Does not resend a statement at the end', () => {
    const echo2 = {...statementEcho, message: { ...statementEcho.message, metadata: { ref: "foo", type: "statement"}}}

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'},
                            {type: 'statement', title: 'foo', ref: 'foo'}]}

    const log = [referral, statementEcho, delivery, echo2]
    const action = getMessage(log, form)[0]
    should.not.exist(action)
  })

  it('Sends a repeat message after an answer to a statement in the end', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'thankyou_screen', title: 'baz', ref: 'baz'}]}

    const log = [referral, tyEcho, delivery, text]
    const action = getMessage(log, form)[0]
    JSON.parse(action.metadata).repeat.should.be.true
  })

  it('Responds to is_echos that come after the delivery watermark', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'thankyou_screen', title: 'baz', ref: 'baz'}]}


    const log = [referral, delivery, {...echo, timestamp: delivery.delivery.watermark}, text]
    const action = getMessage(log, form)[0]
    action.text.should.equal('baz')
  })

  it('Responds to is_echos that come before the delivery watermark', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'thankyou_screen', title: 'baz', ref: 'baz'}]}


    const log = [referral, echo, delivery, , text]
    const action = getMessage(log, form)[0]
    action.text.should.equal('baz')
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
    const action = getMessage(log, form)[0]
    action.should.deep.equal({ text: 'baz', metadata: '{"ref":"baz"}' })
  })

  it('repeats when it misses validation', () => {

    // TODO: this is not unit test, implicitly testing validation of multiple choice.
    // fix this by injecting mock!
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'qux'}, {label: 'quux'}]}}]}

    const log = [referral, echo, delivery, text]
    const action = getMessage(log, form)[0]

    // repeat ref foo with sorry message...
    action.metadata.should.equal('{"repeat":true,"ref":"foo"}')
    action.text.should.contain('Sorry')
  })

  it('If a wait is a statement, it does not send multiple items', () => {

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nwait:\n    type: timeout\n    value: 1 minute'}},
                           {type: 'short_text', title: 'bar', ref: 'bar' }]}

    const wait = { type: 'timeout', value: '1 minute', response: 'baz' }
    const log = [referral]

    const action = getMessage(log, form)
    action.length.should.equal(1)
  })

  it('repeats with custom response when responding to a wait ', () => {

    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nresponseMessage: baz\nwait:\n    type: timeout\n    value: 1 minute'}},
                           {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, text]

    const actions = getMessage(log, form)
    actions.length.should.equal(2)

    // repeat ref foo with sorry message...
    actions[0].metadata.should.equal('{"repeat":true,"ref":"foo"}')
    actions[0].text.should.contain('baz')
    actions[1].text.should.contain('foo')
  })

  it('repeats with default response when responding to a wait without response', () => {

    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo', properties: { description: 'type: wait\nwait:\n    type: timeout\n    value: 1 minute'}},
                           {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, text]

    const actions = getMessage(log, form)

    actions.length.should.equal(2)

    // repeat ref foo with sorry message...
    actions[0].metadata.should.equal('{"repeat":true,"ref":"foo"}')
    actions[0].text.should.contain('No response is necessary')
    actions[1].text.should.contain('foo')
  })

  it('It creates a stitch type message when provided type stitch metadata', () => {

    const form = { logic: [],
                   fields: [{type: 'statement', title: 'foo', ref: 'foo', properties:
                             { description: 'type: stitch\nstitch:\n    form: BAR'}}]}

    const log = [referral]
    const action = getMessage(log, form)[0]
    JSON.parse(action.metadata)['type'].should.equal('stitch')
    JSON.parse(action.metadata)['stitch']['form'].should.equal('BAR')
  })


  it('moves onward when validation succeeds', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [referral, echo, delivery, text]

    const action = getMessage(log, form)[0]
    action.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })

  it('ignores multiple open events at any time', () => {
    should.not.exist(getMessage([referral, delivery, echo, referral], form)[0])
    should.not.exist(getMessage([referral, delivery, echo, text, referral], form)[0])
    should.not.exist(getMessage([referral, referral], form)[0])
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
    const action = getMessage(log, form)[0]
    should.not.exist(action)
  })


  it('Validates a quick reply when valid', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: { value:"quux",ref:"foo" }}}}
    const log = [referral, echo, delivery, response]
    const action = getMessage(log, form)[0]
    action.text.should.equal('bar')
  })


  it('Validates a quick reply with 0 value', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: '0'}, {label: '1'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: { value:0, ref:"foo" }}}}
    const log = [referral, echo, delivery, response]
    const action = getMessage(log, form)[0]
    action.text.should.equal('bar')
  })

  it('Validates a quick reply when payload is string (as in email)', () => {
    const form = { logic: [],
                   fields: [{type: 'email', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: "foo@gmail.com" }}}
    const log = [referral, echo, delivery, response]
    const action = getMessage(log, form)[0]
    action.text.should.equal('bar')
  })


  it('Invalidates a quick reply when invalid', () => {
    const del1 = {...delivery, delivery: { watermark: 5 }}

    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const response = {...qr, message: { quick_reply: { payload: { value:"qux",ref:"foo" }}}}

    const log = [referral, del1, echo, delivery, response]

    const action = getMessage(log, form)[0]
    JSON.parse(action.metadata).repeat.should.be.true
  })

})
