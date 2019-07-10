const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()

const w = require('./waiting')

describe('waitConditionFulfilled', () => {
  it('Is false when there are no events', () => {
    const res = w.waitConditionFulfilled({type: 'timeout', value: '2 days'}, [], Date.now())
    res.should.be.false
  })

  it('Is true when event fulfilled', () => {
    const res = w.waitConditionFulfilled(
      { type: 'moviehouse', value: {id: 'foobar'} },
      [{ event: { type: 'moviehouse', value: {id: 'foobar'} }}],
      Date.now())
    res.should.be.true
  })

  it('Is true when timeout fulfilled', () => {
    const res = w.waitConditionFulfilled(
      { type: 'timeout', value: {id: 'foobar'} },
      [{ event: { type: 'moviehouse', value: {id: 'foobar'} }}],
      Date.now())
    res.should.be.true
  })
})
