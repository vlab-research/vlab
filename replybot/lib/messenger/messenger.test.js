const nock = require('nock')
const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const m = require('./index')
const {MachineIOError} = require('../errors')

const BASE_URL = "https://graph.facebook.com"
const V = "v8.0"

describe('messenger', () => {
  it('should handle ETIMEDOUT from Facebook api by trying 5 times', async () => {

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .times(4)
      .replyWithError({code: 'ETIMEDOUT', connect: false});

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .reply(200, {foo: 'bar'});

    const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    res.should.deep.equal({foo: 'bar'})
  })

  it('should error if ETIMEDOUT from Facebook after 5 times', async () => {
    let error;

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .times(6)
      .replyWithError({code: 'ETIMEDOUT', connect: false});

    try {
      const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    } catch (e) {
      error = e
    }

    error.should.be.instanceof(MachineIOError)
    error.tag.should.equal('NETWORK')
  })


  it('should throw if there is another error from system', async () => {
    let error;

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .replyWithError({code: 'FOO', connect: true});

    try {
      const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    } catch (e) {
      error = e
    }

    error.should.be.instanceof(MachineIOError)
    error.tag.should.equal('NETWORK')
    error.details.code.should.equal('FOO')
  })

  it('should throw MachineIOError if there is a response with an error from Facebook', async () => {
    let error;

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .reply(401, { error: { code: 5 }});

    try {
      const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    } catch (e) {
      error = e
    }

    error.should.be.instanceof(MachineIOError)
    error.tag.should.equal('FB')
    error.details.code.should.equal(5)
  })

  it('should retry if Facebook responds with 1200', async () => {
    let error;

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .times(3)
      .reply(200, { error: {code: 1200}});

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .reply(200, {foo: 'bar'});

    const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    res.should.deep.equal({foo: 'bar'})
  })


  it('should throw MachineIOError when its done retrying on 1200', async () => {
    let error;

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .times(6)
      .reply(200, { error: {code: 1200}});

    try {
      const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    } catch (e) {
      error = e
    }

    error.should.be.instanceof(MachineIOError)
    error.tag.should.equal('FB')
    error.details.code.should.equal(1200)
  })

  it('should retry if Facebook responds with 551', async () => {
    let error;

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .times(3)
      .reply(200, { error: {code: 551 }});

    nock(BASE_URL)
      .post(`/${V}/me/messages`)
      .reply(200, {foo: 'bar'});

    const res = await m.sendMessage('foo', '{ "blah": "blah" }')
    res.should.deep.equal({foo: 'bar'})
  })
})

describe('getUserInfo', () => {
  it('should catch MachineIOError if there is a response with an error from Facebook and return default', async () => {
    let error;

    nock(BASE_URL)
      .get(`/${V}/foo?fields=id,name,first_name,last_name`)
      .reply(401, { error: { code: 5 }});


    const res = await m.getUserInfo('foo', 'token')
    res.name.should.equal('_')
  })
})
