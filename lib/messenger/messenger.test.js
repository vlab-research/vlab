const nock = require('nock')
const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const m = require('./index')

const BASE_URL = "https://graph.facebook.com"

describe('messenger', () => {
  it('should handle ETIMEDOUT from Facebook api by trying 5 times', async () => {


    nock(BASE_URL)
      .post('/v3.2/me/messages')
      .times(4)
      .replyWithError({code: 'ETIMEDOUT', connect: false});

    nock(BASE_URL)
      .post('/v3.2/me/messages')
      .reply(200, {foo: 'bar'});

    const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    res.should.deep.equal({foo: 'bar'})
  })

  it('should error if ETIMEDOUT from Facebook after 5 times', async () => {
    let error;

    nock(BASE_URL)
      .post('/v3.2/me/messages')
      .times(6)
      .replyWithError({code: 'ETIMEDOUT', connect: false});

    try {
      const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    } catch (e) {
      error = e
    }

    error.should.be.instanceof(Error)
  })


  it('should throw if there is another error from system', async () => {
    let error;

    nock(BASE_URL)
      .post('/v3.2/me/messages')
      .replyWithError({code: 'FOO', connect: true});

    try {
      const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    } catch (e) {
      error = e
    }

    error.should.be.instanceof(Error)
    error.code.should.equal('FOO')
  })

  it('should throw if there is a response with an erro from Facebook', async () => {
    let error;

    nock(BASE_URL)
      .post('/v3.2/me/messages')
      .reply(401, { error: {foo: 'bar'}});

    try {
      await m.sendMessage('foo', '{ "blah": "blah" }')
    } catch (e) {
      error = e
    }
    error.should.be.instanceof(Error)
    error.message.should.equal(JSON.stringify({foo: 'bar'}))
  })
})
