const mocha = require('mocha')
const chai = require('chai')
const sinon = require('sinon')
const should = chai.should()
const { Buffered, DBStream } = require('./pgstream')


describe('Buffered', () => {
  it('Returns vals', async () => {

    const f = async () => [1,2,3,4]
    const fn = sinon.fake(f)
    const b = new Buffered(fn)
    const res = []
    for (let a of new Array(8)) {
      const r = await b.next()
      res.push(r)
    }

    fn.callCount.should.equal(2)
    res.should.eql([1,2,3,4,1,2,3,4])
  })

  it('Doesnt break when given null or undefined', async () => {
    const f = async () => null
    const fn = sinon.fake(f)
    const b = new Buffered(fn)
    const res = []

    for (let a of new Array(4)) {
      const r = await b.next()
      res.push(r)
    }

    fn.callCount.should.equal(4)
    res.should.eql([null, null, null, null])
  })
})

describe('DBStream', () => {
  it('Streams data from a continuous function and stops', (done) =>  {

    let i = 0
    const fn = async (lim) => {
      if (i++ < 5) {
        return [[1,2,3], lim+10]
      }
      return [null, null]
    }

    const stream = new DBStream(fn, 0)
    const dats = []
    let finished = false

    stream.on('data', (chunk) => {
      dats.push(chunk)
      if (dats.length === 15) {
        dats[0].should.equal(1)
        dats[14].should.equal(3)
        finished = true
      }
    })
    stream.on('end', () => {
      finished.should.be.true
      done()
    })
  })

  it('Emits an error when the function errors', (done) =>  {
    class TestError extends Error {}

    let i = 0
    const fn = async (lim) => {
      i++
      if (i == 2) {
        throw new TestError('foo')
      }
      else if (i < 2) {
        return [[1,2,3], lim+10]
      }
      return [null, null]
    }

    const stream = new DBStream(fn, 0)
    const dats = []

    stream.on('data', (chunk) => {
    })
    stream.on('error', err => {
      err.should.be.instanceof(TestError)
      done()
    })
  })

  it.only('Emits an descriptive error when the query returns not array', (done) =>  {
    class TestError extends Error {}

    let i = 0
    const fn = async (lim) => {
      i++
      if (i === 1) return undefined
      return [null, null]
    }

    const stream = new DBStream(fn, 0)
    const dats = []

    stream.on('data', (chunk) => {
      done(new Error('this shouldnt happen'))
    })

    stream.on('error', err => {
      err.should.be.instanceof(Error)
      err.message.should.contain('return array of length 2')
      done()
    })
  })
})
