const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const fs = require('fs')
const util = require('util')
const f = require('./form')
const form = JSON.parse(fs.readFileSync('mocks/sample.json'))
const formGame = JSON.parse(fs.readFileSync('mocks/sample-game.json'))
const { parseLogJSON } = require('./utils')
const { echo, statementEcho, repeatEcho, delivery, read, qr, text, multipleChoice, referral} = require('./events.test')



// describe('interpolateField', () => {
//   it('')
// })

describe('getFieldValue', () => {

  it('gets the value of a text field', () => {
    const form = { logic: [], fields: [{ title: 'foo', ref: 'foo'}, {type: 'short_text', title: 'bar', ref: 'bar'}]}
    const log = [echo, delivery, read, text]
    const value = f.getFieldValue({form, log}, 'foo')
    value.should.equal('foo')
  })

  it('gets the value of a payload field', () => {
    const form = { logic: [], fields: [{ title: 'foo', ref: 'foo', type: 'legal'}, {type: 'short_text', title: 'bar', ref: 'bar'}]}
    const log = [echo, delivery, read, multipleChoice]
    const value = f.getFieldValue({form, log}, 'foo')
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

describe('getFromMetadata', () => {
  it('works with unicode Facebook names', () => {
    const name = '小飼弾'
    const ctx = {log: [referral, text], user: { name }}
    f.getFromMetadata(ctx, 'name').should.equal(name)

  })

  it('works with unicode url values', () => {
    const name = '小飼弾'
    const uni = encodeURIComponent(name)
    const ref2 = {...referral, referral: {...referral.referral, ref: `form.BAR.foo.${uni}`}}

    const ctx = {log: [ref2, text], user: { name: 'Foo Bazzle'}}
    f.getFromMetadata(ctx, 'foo').should.equal(name)
  })
})


describe('interpolateField', () => {
  it('works with hidden fields from user', () => {

    const ctx = {log: [referral, text], user: { name: 'Foo Bazzle'}}
    const i = f.interpolateField(ctx, { title: 'hello {{ hidden:name }}'})
    i.title.should.equal('hello Foo Bazzle')
  })

  it('works with hidden fields from referral', () => {
    const name = '小飼弾'
    const uni = encodeURIComponent(name)
    const ref2 = {...referral, referral: {...referral.referral, ref: `form.BAR.foo.${uni}`}}
    const ctx = {log: [ref2, text], user: { name: 'Foo Bazzle'}}
    const i = f.interpolateField(ctx, { title: 'hello {{ hidden:foo }}'})
    i.title.should.equal(`hello ${name}`)
  })

  it('works with previously answered fields', () => {
    const ctx = {log: [referral, echo, delivery, read, qr, statementEcho, read], user: {}}
    const i = f.interpolateField(ctx, { title: 'You chose: {{ field:foo }}'})
    i.title.should.equal(`You chose: Continue`)
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

describe('jump', () => {
  it('makes jump when required and not when not', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: { ref: "378caa71-fc4f-4041-8315-02b6f33616b9"}}}

    const numLow = {...text, message: { text: '10' }}
    const numGood = {...text, message: { text: '18' }}

    const yes = f.jump({ form, log: [text, echo2, delivery, read, numGood]}, form.logic[0])
    yes.should.equal('0ebfe765-0275-48b2-ad2d-3aacb5bc6755')


    const no = f.jump({ form, log: [text, echo2, delivery, read, numLow]}, form.logic[0])
    no.should.equal('3edb7fcc-748c-461c-bacd-593c043c5518')
  })

  it('makes jump with a correct number answer in a string', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: { ref: "c3432d3d-f786-4a38-8ac7-b50c1dfdb1ba"}}}

    const resp = {...text, message: { text: '7.2' }}
    const no = f.jump({form: formGame, log: [text, echo2, delivery, read, resp]}, formGame.logic[22])
    no.should.equal('1fac0275-3b85-4037-aed9-f2c106876337')

    const resp2 = {...text, message: { text: '7.5' }}
    const yes = f.jump({form: formGame, log: [text, echo2, delivery, read, resp2]}, formGame.logic[22])
    yes.should.equal('fb74abb2-ed4c-42bb-bc80-b0677f992d01')
  })

  it('doesnt make jump if required field is not answered', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: { ref: "378caa71-fc4f-4041-8315-02b6f33616b9"}}}

    const no = f.jump({ form, log: [text, echo2]}, form.logic[0])
    no.should.equal('3edb7fcc-748c-461c-bacd-593c043c5518')
  })

  // TODO: should this throw??????
  it('doesnt make jump if required field doesnt exist', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: { ref: "378caa71-fc4f-4041-8315-02b6f33616b9"}}}

    const no = f.jump({ form, log: [text]}, form.logic[0])
    no.should.equal('3edb7fcc-748c-461c-bacd-593c043c5518')
  })

  it('it throws if it cannot find an action', () => {

    const echo2 = {...echo, message: { ...echo.message, metadata: { ref: "baz"}}}

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

    f.jump.bind(null, { form, log: []}, logic).should.throw()
  })
})

describe('getCondition', () => {
  it('works with always true', () => {
    const con = form.logic[2].actions[0].condition
    f.getCondition({ form, log:[]}, '', con).should.be.true
  })

  it('works with number equals - type casting!', () => {

    const echoBaz = {...echo, message: { ...echo.message, metadata: '{ "ref": "baz"}'}}
    const num = {...text, message: { text: '10' }}

    const cond = { op: 'is',
                     vars: [ { type: 'field', value: 'baz' },
                             { type: 'constant', value: 10 } ] }

    f.getCondition({ form, log: [echoBaz, delivery, read, num]}, '', cond).should.be.true
  })

  it('works with number not equals - type casting!', () => {
    const echoBaz = {...echo, message: { ...echo.message, metadata: '{ "ref": "baz"}'}}
    const num = {...text, message: { text: '11' }}

    const cond = { op: 'is',
                     vars: [ { type: 'field', value: 'baz' },
                             { type: 'constant', value: 10 } ] }

    f.getCondition({ form, log: [echoBaz, delivery, read, num]}, '', cond).should.be.false
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
