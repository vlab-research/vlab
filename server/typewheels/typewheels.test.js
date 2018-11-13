const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const fs = require('fs')

const t = require('./typewheels')

const r = JSON.parse(fs.readFileSync('mocks/sample.json'))

[
  { sender: { id: '1800244896727776' },
    recipient: { id: '1051551461692797' },
    timestamp: 1542108796197,
    message: { text: 'Yes, Ok' } },
  { sender: { id: '1800244896727776' },
    recipient: { id: '1051551461692797' },
    timestamp: 1542106624151,
    read: { } },
  { sender: { id: '1051551461692797' },
    recipient: { id: '1800244896727776' },
    timestamp: 1542106597790,
    message:
     { is_echo: true,
       metadata: 'foo',
       text: 'Do you wish to share this?',
       attachments: [Array] } },
  { sender: { id: '1800244896727776' },
    recipient: { id: '1051551461692797' },
    timestamp: 1542106596197,
    message: { text: 'foo' } }
]


describe('getField', () => {
  it('gets the field if it exists', () => {
    const field = '4cc5c31b-6d23-4d50-8536-7abf1cdf0782'
    t.getField(r,field).should.deep.equal(r.fields[0])
  })
  it('returns undefined otherwise', () => {
    const field = 'foo'
    should.not.exist(t.getField(r,field))
  })
})

describe('getCondition', () => {
  it('works with always true', () => {
    const con = r.logic[2].actions[0].condition
    t.getCondition(r, con).should.be.true
  })
})
