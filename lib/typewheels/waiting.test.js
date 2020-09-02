const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const chrono = require('chrono-node')
const w = require('./waiting')

describe('waitConditionFulfilled', () => {
  const start = Date.now()

  it('Is false when there are no events', () => {
    const res = w.waitConditionFulfilled({type: 'timeout', value: '2 days'}, [], Date.now())
    res.should.be.false
  })

  it('Is true when event fulfilled', () => {
    const res = w.waitConditionFulfilled(
      { type: 'external', value: {type: 'moviehouse:play', id: 'foobar'} },
      [{ event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar'} }}],
      Date.now())
    res.should.be.true
  })

  it('Is true when timeout fulfilled', () => {
    const res = w.waitConditionFulfilled(
      { type: 'timeout', value: '1 hour' },
      [{ event: {type: 'timeout', value: Date.now() + 1000*60*60 }}],
      Date.now())
    res.should.be.true
  })


  it('Is true when timeout overfulfilled', () => {
    const res = w.waitConditionFulfilled(
      { type: 'timeout', value: '1 hour' },
      [{ event: {type: 'timeout', value: Date.now() + 2000*60*60 }}],
      Date.now())
    res.should.be.true
  })


  it('Is true when timeout overfulfilled and delivered in rfc3339 rounded up to nearest second', () => {
    const now = 1599084716601
    const rfc = '2020-09-02T23:11:57.000Z'

    const res = w.waitConditionFulfilled(
      { type: 'timeout', value: '1 hour' },
      [{ event: {type: 'timeout', value: rfc }}],
      now)
    res.should.be.true
  })

  it('operator:or -- true when one event is fulfilled', () => {

    const wait = { op: 'or', vars: [
      {type: 'timeout', value: '1 hour'},
      {type: 'external', value: { type: 'moviehouse:play', id: 'foobar'}}
    ]}

    const res = w.waitConditionFulfilled(
      wait,
      [{ event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar'} }}],
      Date.now())

    res.should.be.true
  })

  it('operator:or -- false when no event is fulfilled', () => {

    const wait = { op: 'or', vars: [
      {type: 'timeout', value: '1 hour'},
      {type: 'external', value: { type: 'moviehouse:play', id: 'foobar'}}
    ]}

    const res = w.waitConditionFulfilled(
      wait,
      [{ event: { type: 'external', value: {type: 'moviehouse:load', id: 'foobar'} }}],
      Date.now())

    res.should.be.false
  })

  it('operator:or -- true when both events are fulfilled', () => {

    const wait = { op: 'or', vars: [
      {type: 'timeout', value: '1 hour'},
      {type: 'external', value: { type: 'moviehouse:play', id: 'foobar'}}
    ]}

    const res = w.waitConditionFulfilled(
      wait,
      [{ event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar'} }}],
      Date.now() - 1000*60*60)

    res.should.be.true
  })

  it('operator:or -- true when any of many events are fulfilled', () => {

    const wait = { op: 'or', vars: [
      {type: 'timeout', value: '1 hour'},
      {type: 'external', value: { type: 'moviehouse:pause', id: 'foobar'}},
      {type: 'external', value: { type: 'moviehouse:play', id: 'foobar'}}
    ]}

    const res = w.waitConditionFulfilled(
      wait,
      [{ event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar'} }}],
      Date.now() - 1000*60*60)

    res.should.be.true
  })

  it('operator:or -- false when none of many events are fulfilled', () => {

    const wait = { op: 'or', vars: [
      {type: 'timeout', value: '1 hour'},
      {type: 'external', value: { type: 'moviehouse:pause', id: 'foobar'}},
      {type: 'external', value: { type: 'moviehouse:play', id: 'foobar'}}
    ]}

    const res = w.waitConditionFulfilled(
      wait,
      [{ event: { type: 'external', value: {type: 'moviehouse:butt', id: 'foobar'} }}],
      Date.now() - 1000*60*60)

    res.should.be.false
  })



  it('operator:and -- true when all events are fulfilled', () => {

    const wait = { op: 'and', vars: [
      {type: 'timeout', value: '1 hour'},
      {type: 'external', value: { type: 'moviehouse:play', id: 'foobar'}},
      {type: 'external', value: { type: 'moviehouse:pause', id: 'foobar'}}
    ]}

    const timeoutDate = chrono.parseDate('1 hour', new Date(start))

    const res = w.waitConditionFulfilled(
      wait,
      [{ event: {type: 'timeout', value: timeoutDate }},
       { event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar'} }},
       { event: { type: 'external', value: {type: 'moviehouse:pause', id: 'foobar'} }}],
      start)

    res.should.be.true
  })

  it('operator:and -- false when only one event is fulfilled', () => {

    const wait = { op: 'and', vars: [
      {type: 'timeout', value: '1 hour'},
      {type: 'external', value: { type: 'moviehouse:play', id: 'foobar'}}
    ]}

    const res = w.waitConditionFulfilled(
      wait,
      [{ event: { type: 'external', value: {type: 'moviehouse:play', id: 'foobar'} }}],
      Date.now() - 1000*60*30)

    res.should.be.false
  })


  it('operator:and -- false when no event is fulfilled', () => {

    const wait = { op: 'and', vars: [
      {type: 'timeout', value: '1 hour'},
      {type: 'external', value: { type: 'moviehouse:play', id: 'foobar'}}
    ]}

    const res = w.waitConditionFulfilled(
      wait,
      [{ event: { type: 'external', value: {type: 'moviehouse:load', id: 'foobar'} }}],
      Date.now() - 1000*60*30)

    res.should.be.false
  })
})
