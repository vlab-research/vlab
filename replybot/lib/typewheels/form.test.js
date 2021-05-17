const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const fs = require('fs')
const util = require('util')
const f = require('./form')
const form = JSON.parse(fs.readFileSync('mocks/sample.json'))
const formGame = JSON.parse(fs.readFileSync('mocks/sample-game.json'))
const { parseLogJSON, getMetadata } = require('./utils')
const { echo, statementEcho, repeatEcho, delivery, qr, text, multipleChoice, referral} = require('./events.test')


describe('getFieldValue', () => {

  it('gets the value of a text field', () => {
    const qa = [['foo', 'foo']]
    const value = f.getFieldValue(qa, 'foo')
    value.should.equal('foo')
  })

  // TODO: should this throw?
  it('returns null if the field doesnt exist', () => {
    const qa = []
    const value = f.getFieldValue(qa, 'foo')
    should.not.exist(value)
  })
})



describe('getField', () => {
  it('throws with a useful message when field not found in form', () => {
    const ctx = { form, user: { name: 'bar', id: 'foo' }}
    const fn = f.getField.bind(null, ctx, 'baz')
    fn.should.throw(/foo/) // user
    fn.should.throw(/baz/) // field
    fn.should.throw(/ODf5n7/) // form
  })
})

describe('getFromMetadata', () => {
  it('works with unicode Facebook names', () => {
    const name = '小飼弾'
    const ctx = { user: { name }}
    f.getFromMetadata(ctx, 'name').should.equal(name)
  })

  it('works with false values', () => {
    const ctx = { md: { event__foo_success: false }}
    f.getFromMetadata(ctx, 'event__foo_success').should.equal(false)
  })

  it('works with unicode Facebook names', () => {
    const ctx = { md: { seed: 125 }}
    f.getFromMetadata(ctx, 'seed_5').should.equal(1)
    f.getFromMetadata(ctx, 'seed_1').should.equal(1)
    f.getFromMetadata(ctx, 'seed_4').should.equal(2)
    f.getFromMetadata(ctx, 'seed_3').should.equal(3)
  })

  it('works with unicode url values', () => {
    const name = '小飼弾'
    const uni = encodeURIComponent(name)
    const ref2 = {...referral, referral: {...referral.referral, ref: `form.BAR.foo.${uni}`}}
    const md = getMetadata(ref2)

    const ctx = {md, user: { name: 'Foo Bazzle'}}
    f.getFromMetadata(ctx, 'foo').should.equal(name)
  })
})

describe('_splitUrls', () => {
  it('groups by url', () => {
    const split = f._splitUrls('hello https://foo.com?key={{bar}} baz http://hello.us')
    split.should.deep.equal([
      ['text', 'hello '],
      ['url', 'https://foo.com?key={{bar}}'],
      ['text', ' baz '],
      ['url', 'http://hello.us']
    ])
  })

  it('works with url at beginning', () => {
    const split = f._splitUrls('https://foo.com?key={{bar}} baz')
    split.should.deep.equal([
      ['url', 'https://foo.com?key={{bar}}'],
      ['text', ' baz']
    ])
  })

  it('works with only url', () => {
    const split = f._splitUrls('https://foo.com?key={{bar}}')
    split.should.deep.equal([
      ['url', 'https://foo.com?key={{bar}}']
    ])
  })

  it('works with text at end', () => {
    const split = f._splitUrls('hello https://foo.com?key={{bar}} baz')
    split.should.deep.equal([
      ['text', 'hello '],
      ['url', 'https://foo.com?key={{bar}}'],
      ['text', ' baz']
    ])
  })

  it('works with no url', () => {
    const split = f._splitUrls('hello baz')
    split.should.deep.equal([
      ['text', 'hello baz'],
    ])
  })
})

describe('interpolateField', () => {
  it('works with hidden fields from user', () => {

    const ctx = {log: [referral, text], user: { name: 'Foo Bazzle'}}
    const i = f.interpolateField(ctx, [], { title: 'hello {{hidden:name}}'})
    i.title.should.equal('hello Foo Bazzle')
  })

  it('works with hidden fields from referral', () => {
    const name = '小飼弾'
    const uni = encodeURIComponent(name)
    const ref2 = {...referral, referral: {...referral.referral, ref: `form.BAR.foo.${uni}`}}
    const md = getMetadata(ref2)
    const ctx = {md, user: { name: 'Foo Bazzle'}}
    const i = f.interpolateField(ctx, [], { title: 'hello {{hidden:foo}}'})
    i.title.should.equal(`hello ${name}`)
  })

  it('works with previously answered fields', () => {
    const ctx = {log: [], user: {}}
    const i = f.interpolateField(ctx, [['foo', 'Continue']], { title: 'You chose: {{field:foo}}'})
    i.title.should.equal(`You chose: Continue`)
  })

  it('Throws if the field is unanswered', () => {
    const ctx = {log: [], user: {}}
    const fn = f.interpolateField.bind(null, ctx, [], { title: 'You chose: {{field:foo}}'})
    fn.should.throw()
  })

  it('works with description', () => {
    const ctx = {log: [], user: { name: 'Foo Bazzle'}}
    const i = f.interpolateField(ctx, [], { properties: {description: 'name: {{hidden:name}}'}})
    i.properties.description.should.equal('name: Foo Bazzle')
  })

  it('encodes urls interpolation', () => {
    const ctx = {log: [], user: { name: 'Foo Bazzle'}}
    const i = f.interpolateField(ctx, [], { properties: {description: 'foo: bar\nurl: https://hello.com/?name={{hidden:name}}'}})
    i.properties.description.should.equal('foo: bar\nurl: https://hello.com/?name=Foo%20Bazzle')
  })

  it('encodes urls interpolation inside text', () => {
    const ctx = {log: [], user: { name: 'Foo Bazzle'}}
    const i = f.interpolateField(ctx, [], { title: 'Please visit: https://hello.com/?name={{hidden:name}}'})
    i.title.should.equal('Please visit: https://hello.com/?name=Foo%20Bazzle')
  })

})

describe('addCustomType', () => {
  it('changes the type from the yaml if exists', () => {
    const field = {type: 'statement', title: 'foo', ref: 'foo', properties: { description: 'type: share'}}
    const out = f.addCustomType(field)
    out.type.should.equal('share')
  })

  it('adds additional fields into the md property', () => {
    const field = {type: 'statement', title: 'foo', ref: 'foo', properties: { description: 'type: share\nurl: foo'}}
    const out = f.addCustomType(field)
    out.md.url.should.equal('foo')
  })

  it('doesnt change it if no yaml', () => {
    const field = {type: 'statement', title: 'foo', ref: 'foo', properties: { description: '#notyaml&foo=bar'}}
    const out = f.addCustomType(field)
    out.type.should.equal('statement')
  })

  it('doesnt change the type with a different yaml', () => {
    const field = {type: 'statement', title: 'foo', ref: 'foo', properties: { description: 'foo: bar'}}
    const out = f.addCustomType(field)
    out.type.should.equal('statement')
  })

  it('doesnt change anything with no description', () => {
    const field = {type: 'multiple_choice', title: 'foo', ref: 'foo', properties: {choices: [{label: 'qux'}, {label: 'quux'}]}}
    const out = f.addCustomType(field)
    out.type.should.equal('multiple_choice')
  })
})


describe('jump', () => {
  it('makes jump when required and not when not', () => {

    const qaBad = [['378caa71-fc4f-4041-8315-02b6f33616b9', '10']]
    const qaGood = [['378caa71-fc4f-4041-8315-02b6f33616b9', '18']]

    const yes = f.jump({ form }, qaGood, form.logic[0])
    yes.should.equal('0ebfe765-0275-48b2-ad2d-3aacb5bc6755')


    const no = f.jump({ form }, qaBad, form.logic[0])
    no.should.equal('3edb7fcc-748c-461c-bacd-593c043c5518')
  })

  it('makes jump with a correct number answer in a string', () => {
    const echo2 = {...echo, message: { ...echo.message, metadata: { ref: "c3432d3d-f786-4a38-8ac7-b50c1dfdb1ba"}}}

    const qa = [['c3432d3d-f786-4a38-8ac7-b50c1dfdb1ba',  '7.2']]
    const qa2 = [['c3432d3d-f786-4a38-8ac7-b50c1dfdb1ba',  '7.5']]

    const no = f.jump({form: formGame}, qa, formGame.logic[22])
    no.should.equal('1fac0275-3b85-4037-aed9-f2c106876337')

    const yes = f.jump({form: formGame}, qa2, formGame.logic[22])
    yes.should.equal('fb74abb2-ed4c-42bb-bc80-b0677f992d01')
  })

  // TODO: should this throw??????
  it('doesnt make jump if required field doesnt exist', () => {

    const no = f.jump({ form }, [], form.logic[0])
    no.should.equal('3edb7fcc-748c-461c-bacd-593c043c5518')
  })

  // TODO: this should be checked at form load time
  it('it defaults to the next field if it cannot fulfil logic jump for any reason', () => {
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

    let fallback = f.jump({ form }, [['baz', '14']], logic)
    fallback.should.equal(form.fields[0].ref)

    fallback = f.jump({ form }, [], logic)
    fallback.should.equal(form.fields[0].ref)
  })
})

describe('getCondition', () => {
  it('works with always true', () => {
    const con = form.logic[2].actions[0].condition
    f.getCondition({ form }, [], '', con).should.be.true
  })

  it('works with number equals and not equals is and is not - casts types from strings', () => {
    const cond = { op: 'is',
                     vars: [ { type: 'field', value: 'baz' },
                             { type: 'constant', value: 10 } ] }

    const qa = [['baz', '10']]

    f.getCondition({ form }, qa, '', cond).should.be.true
    f.getCondition({ form }, qa, '', {...cond, op: 'equal'}).should.be.true
    f.getCondition({ form }, qa, '', {...cond, op: 'is_not'}).should.be.false
    f.getCondition({ form }, qa, '', {...cond, op: 'not_equal'}).should.be.false
  })

  it('works with boolean strings in form and true boolean in metadata', () => {
    const cond = { op: 'is',
                     vars: [ { type: 'hidden', value: 'baz' },
                             { type: 'constant', value: 'true' } ] }

    const qa = []
    const md = { baz: true }

    f.getCondition({ form, md }, qa, '', cond).should.be.true
    f.getCondition({ form, md }, qa, '', {...cond, op: 'equal'}).should.be.true
    f.getCondition({ form, md }, qa, '', {...cond, op: 'is_not'}).should.be.false
    f.getCondition({ form, md }, qa, '', {...cond, op: 'not_equal'}).should.be.false
  })

  it('works with lower_equal_than operator on numbers', () => {
    const cond = { op: 'lower_equal_than',
                     vars: [ { type: 'field', value: 'baz' },
                             { type: 'constant', value: 10 } ] }

    const qa = [['baz', '10']]

    f.getCondition({ form }, qa, '', cond).should.be.true
    f.getCondition({ form }, qa, '', {...cond, op: 'greater_equal_than'}).should.be.true
  })

  it('works with "and" and "or" operators', () => {

    const cond = {
      "op": "and",
      "vars": [
        {
          "op": "is",
          "vars": [
            {
              "type": "field",
              "value": "baz"
            },
            {
              "type": "constant",
              "value": true
            }
          ]
        },
        {
          "op": "is",
          "vars": [
            {
              "type": "field",
              "value": "qux"
            },
            {
              "type": "constant",
              "value": true
            }
          ]
        }
      ]
    }

    const qa = [['baz',  true], ['qux', true]]
    const qa2 = [['baz', true], ['qux', false]]

    f.getCondition({ form }, qa, '', cond).should.be.true
    f.getCondition({ form }, qa, '', {...cond, op: 'or' }).should.be.true
    f.getCondition({ form }, qa2, '', cond).should.be.false
    f.getCondition({ form }, qa2, '', {...cond, op: 'or' }).should.be.true
  })


  it('works with triple operators', () => {

    const cond = {
      "op": "or",
      "vars": [
        {
          "op": "equal",
          "vars": [
            {
              "type": "hidden",
              "value": "seed_16"
            },
            {
              "type": "constant",
              "value": "9"
            }
          ]
        },
        {
          "op": "equal",
          "vars": [
            {
              "type": "hidden",
              "value": "seed_16"
            },
            {
              "type": "constant",
              "value": "10"
            }
          ]
        },
        {
          "op": "equal",
          "vars": [
            {
              "type": "hidden",
              "value": "seed_16"
            },
            {
              "type": "constant",
              "value": "11"
            }
          ]
        },
        {
          "op": "equal",
          "vars": [
            {
              "type": "hidden",
              "value": "seed_16"
            },
            {
              "type": "constant",
              "value": "12"
            }
          ]
        }
      ]
    }

    const qa = []

    f.getCondition({ form, md: {seed: 0} }, qa, '', cond).should.be.false
    f.getCondition({ form, md: {seed: 7} }, qa, '', cond).should.be.false
    f.getCondition({ form, md: {seed: 8} }, qa, '', cond).should.be.true
    f.getCondition({ form, md: {seed: 1870657866 } }, qa, '', cond).should.be.true
  })


  it('works with a choice on a previous field', () => {
    const cond = {
      op: "is",
      vars: [
        {
          type: "field",
          value: "44659a5e-3640-460a-9614-bd3ae8311043"
        },
        {
          type: "choice",
          value: "d3bc0725-4371-42ae-8bb4-0492eff445fb"
        }
      ]
    }

    const qa = [['44659a5e-3640-460a-9614-bd3ae8311043', 'Female']]
    f.getCondition({ form }, qa, '', cond).should.be.true
  })

  it('works with a hidden field', () => {
    const cond = {
      op: "is",
      vars: [
        {
          type: "hidden",
          value: "bar"
        },
        {
          type: "constant",
          value: "foo"
        }
      ]
    }

    f.getCondition({ form, md: { bar: 'foo'} }, [], '', cond).should.be.true
  })

  it('works with the hidden random seed field', () => {
    const cond = {
      op: "equal",
      vars: [
        {
          type: "hidden",
          value: "seed_5"
        },
        {
          type: "constant",
          value: "1"
        }
      ]
    }

    f.getCondition({ form, md: { seed: 10} }, [], '', cond).should.be.true
    f.getCondition({ form, md: { seed: 11} }, [], '', cond).should.be.false
  })


  it('works with number not equals - type casting!', () => {
    const cond = { op: 'is',
                     vars: [ { type: 'field', value: 'baz' },
                             { type: 'constant', value: 10 } ] }

    const qa = [['baz', '11']]

    f.getCondition({ form }, qa, '', cond).should.be.false
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
