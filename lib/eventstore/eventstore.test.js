const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const sinon = require('sinon')
const s = require('./index')

describe('_resolve', () => {

  it('returns with event if not there', () => {
    s._resolve(['foo', 'bar'], 'baz').should.deep.equal(['foo', 'bar', 'baz'])
  })

  it('returns with event if there', () => {
    s._resolve(['foo', 'bar', 'baz'], 'baz').should.deep.equal(['foo', 'bar', 'baz'])
  })

  it('returns with event if there but not the last', () => {
    s._resolve(['foo', 'baz', 'bar'], 'baz').should.deep.equal(['foo', 'baz'])
    s._resolve(['foo', 'baz', 'bar'], 'foo').should.deep.equal(['foo'])
  })


  it('returns with event if empty or undefined', () => {
    s._resolve([], 'baz').should.deep.equal(['baz'])
    s._resolve(undefined, 'baz').should.deep.equal(['baz'])
  })
})

describe('EventStore', () => {
  it('returns just the event when db returns nothing', async () => {
    const db = { get: sinon.fake.returns(undefined) }
    const e = new s.EventStore(db)
    const events = await e.getEvents('foo', 'baz')
    events.should.deep.equal(['baz'])
    e.cache.foo.should.deep.equal(['baz'])
  })

  it('updates database when db returns something', async () => {
    const db = { get: sinon.fake.returns(['bar', 'baz']) }
    const e = new s.EventStore(db)
    const events = await e.getEvents('foo', 'baz')
    events.should.deep.equal(['bar', 'baz'])
    e.cache.foo.should.deep.equal(['bar', 'baz'])
  })
})
