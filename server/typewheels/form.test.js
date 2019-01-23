const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const fs = require('fs')

const f = require('./form')
const form = JSON.parse(fs.readFileSync('mocks/sample.json'))
const { parseLogJSON } = require('./utils')
const { echo, statementEcho, repeatEcho, delivery, read, qr, text, multipleChoice, referral} = require('./events.test')



describe('getFieldValue', () => {

  it('gets the value of a text field', () => {
    const form = { logic: [], fields: [{ title: 'foo', ref: 'foo'}, {type: 'short_text', title: 'bar', ref: 'bar'}]}
    const log = [echo, delivery, read, text]
    const value = f.getFieldValue(form, log, 'foo')
    value.should.equal('foo')
  })

  it('gets the value of a payload field', () => {
    const form = { logic: [], fields: [{ title: 'foo', ref: 'foo', type: 'legal'}, {type: 'short_text', title: 'bar', ref: 'bar'}]}
    const log = [echo, delivery, read, multipleChoice]
    const value = f.getFieldValue(form, log, 'foo')
    value.should.be.true
  })
  // it('gets the field if it exists', () => {
  //   const field = '4cc5c31b-6d23-4d50-8536-7abf1cdf0782'
  //   f.getField(r,field).should.deep.equal(r.fields[0])
  // })
  // it('returns undefined otherwise', () => {
  //   const field = 'foo'
  //   should.not.exist(t.getField(r,field))
  // })
})


describe('getWatermark', () => {
  it('returns watermarks', () => {
    const log = [text, read, delivery]
    f.getWatermark('delivery', log).should.equal(15)
    f.getWatermark('read', log).should.equal(10)
  })

  it('returns watermark with multiple', () => {
    const d2 = {...delivery, delivery: {watermark: 25}}
    const log = [text, read, delivery, d2]
    f.getWatermark('delivery', log).should.equal(25)
    f.getWatermark('read', log).should.equal(10)
  })

})

describe('getLogState', () => {
  it('translates simple state', () => {
    const log = [text]
    f.getLogState(log).should.deep.equal([])
  })

  it('Gets whole history of complex state', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "bar"}'}}
    const log = [text, echo, delivery, read, multipleChoice, text, echo2]
    const history = f.getLogState(log)
    history.map(i => i[0]).should.deep.equal(['foo', 'bar'])
  })

  it('Gets whole history of complex state when postbacks are in order', () => {
    const echo2 = {...echo, timestamp: 25, message: { ...echo.message, metadata: '{ "ref": "bar"}'}}

    const delivery2 = {...delivery, delivery: {watermark: 25}}
    const read2 = {...delivery, read: {watermark: 25}}

    const log = [echo, delivery, read, text, echo2, delivery2, read2, text]
    const history = f.getLogState(log)

    // correctly assigns first text to first echo
    history[0][1].length.should.equal(1)
    history[0][1][0].message.text.should.equal('foo')

    // assigns second text to echo2
    history[1][1].length.should.equal(1)
    history[1][1][0].message.text.should.equal('foo')
  })

  it('Gets whole history of complex state when postbacks out of order', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "bar"}'}}
    // const read2 =
    const log = [text, echo, delivery, read, echo2, multipleChoice, read, text]
    const history = f.getLogState(log)

    // correctly assigns multipleChoice to first echo
    history[0][1].length.should.equal(1)
    history[0][1][0].postback.payload.should.deep.equal({
      value: true,
      ref: 'foo'
    })

    // assigns second text to echo2
    history[1][1].length.should.equal(1)
    history[1][1][0].message.text.should.equal('foo')
  })

})

const util = require('util')

describe('jump', () => {
  it('makes jump when required and not when not', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "378caa71-fc4f-4041-8315-02b6f33616b9"}'}}

    const numLow = {...text, message: { text: '10' }}
    const numGood = {...text, message: { text: '18' }}

    const yes = f.jump(form, [text, echo2, delivery, read, numGood], form.logic[0])
    yes.should.equal('0ebfe765-0275-48b2-ad2d-3aacb5bc6755')

    const no = f.jump(form, [text, echo2, delivery, read, numLow], form.logic[0])
    no.should.equal('3edb7fcc-748c-461c-bacd-593c043c5518')
  })

  it('doesnt make jump if required field is not answered', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "378caa71-fc4f-4041-8315-02b6f33616b9"}'}}

    const no = f.jump(form, [text, echo2], form.logic[0])
    no.should.equal('3edb7fcc-748c-461c-bacd-593c043c5518')
  })


  // TODO: should this throw??????
  it('doesnt make jump if required field doesnt exist', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "378caa71-fc4f-4041-8315-02b6f33616b9"}'}}

    const no = f.jump(form, [text], form.logic[0])
    no.should.equal('3edb7fcc-748c-461c-bacd-593c043c5518')
  })

  it('it throws if it cannot find an action', () => {



    const echo2 = {...echo, message: { ...echo.message, metadata: '{ "ref": "baz"}'}}

    const logic = { type: 'field',
                    actions:
                    [ { action: 'jump',
                        details:
                        { to: { type: 'field', value: 'foo' }},
                        condition:
                        { op: 'is',
                          vars:
                          [ { type: 'field', value: 'baz' },
                            { type: 'constant', value: '15' } ] }
                      }] }

    f.jump.bind(null, form, [], logic).should.throw()
  })
})

describe('getCondition', () => {
  it('works with always true', () => {
    const con = form.logic[2].actions[0].condition
    f.getCondition(form, [], con).should.be.true
  })

  it('works with number equals - type casting!', () => {

    const echoBaz = {...echo, message: { ...echo.message, metadata: '{ "ref": "baz"}'}}
    const num = {...text, message: { text: '10' }}

    const cond = { op: 'is',
                     vars: [ { type: 'field', value: 'baz' },
                             { type: 'constant', value: 10 } ] }

    f.getCondition(form, [echoBaz, delivery, read, num], cond).should.be.true
  })

  it('works with number not equals - type casting!', () => {
    const echoBaz = {...echo, message: { ...echo.message, metadata: '{ "ref": "baz"}'}}
    const num = {...text, message: { text: '11' }}

    const cond = { op: 'is',
                     vars: [ { type: 'field', value: 'baz' },
                             { type: 'constant', value: 10 } ] }

    f.getCondition(form, [echoBaz, delivery, read, num], cond).should.be.false
  })
})

describe('Machine', () => {
  let machine;

  beforeEach(() => {
    machine = new f.Machine()
  })

  it('gets the correct start text (the first field)', () => {
    const start = machine.exec({ state: 'START', form: 'foo'}, form)
    start.attachment.payload.text.should.equal(form.fields[0].title)
  })

  it ('it gets the next question when there is a next', () => {
    const form = { logic: [], fields: [{ title: 'foo', ref: 'foo', 'type': 'short_text'}, {type: 'short_text', title: 'bar', ref: 'bar'}]}
    const log = [echo, delivery, read, text]
    const nxt = machine.exec({state: 'QA', question: 'foo'}, form, log)
    nxt.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })

  it('it gets the next question when there is a next 2', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const log = [echo, delivery, read, text]
    const nxt = machine.exec({state: 'QA', question: 'foo'}, form, log)
    nxt.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })

  it('it repeats a statement, which is always invalid to answer', () => {
    const form = { logic: [],
                   fields: [{type: 'statement', title: 'bar', ref: 'bar'}]}

    const log = [echo, delivery, read, text]

    const nxt = machine.exec({state: 'QA', question: 'bar'}, form, log)

    JSON.parse(nxt.metadata).repeat.should.be.true
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

    const log = [echo, delivery, read, text]
    const nxt = machine.exec({state: 'QA', question: 'foo'}, form, log)
    nxt.should.deep.equal({ text: 'baz', metadata: '{"ref":"baz"}' })
  })

  it('repeats when it misses validation', () => {

    // TODO: this is not unit test, implicitly testing validation of multiple choice.
    // fix this by injecting mock!
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'qux'}, {label: 'quux'}]}}]}

    const nxt = machine.exec({state: 'QA', question: 'foo', response: 'foo'}, form, [])

    // repeat ref foo with sorry message...
    nxt.metadata.should.equal('{"repeat":true,"ref":"foo"}')
    nxt.text.should.contain('Sorry')
  })

  it('moves onward when validation succeeds misses validation', () => {
    const form = { logic: [],
                   fields: [{type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'foo'}, {label: 'quux'}]}},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}


    const nxt = machine.exec({state: 'QA', question: 'foo', response: 'foo'}, form, [])
    nxt.should.deep.equal({ text: 'bar', metadata: '{"ref":"bar"}' })
  })

  it('repeats the question when given a repeat state', () => {
    const form = { logic: [],
                   fields: [{type: 'short_text', title: 'foo', ref: 'foo'},
                            {type: 'short_text', title: 'bar', ref: 'bar'}]}

    const nxt = machine.exec({state: 'REPEAT', question: 'foo'}, form, [])
    nxt.should.deep.equal({ text: 'foo', metadata: '{"ref":"foo"}' })
  })
})

// TODO: move this to VALIDATORS module!
// describe('formValidator', () => {
//   it('deals with empty form with a helpful error', () => {
//     const badform = {...form, fields: []}
//     const fn = f.formValidator.bind(null, badform)
//     fn.should.throw(TypeError)
//   })
// })
