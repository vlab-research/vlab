// const nock = require('nock')
const mocha = require('mocha')
const chai = require('chai')
const should = chai.should()
const {Machine} = require('./transition')
const {MachineIOError} = require('../errors')

// const BASE_URL = "https://graph.facebook.com"

describe('machine.run', () => {
  it('returns STATE_TRANSITION error if transition throws', async () => {

    const m = new Machine()
    m.transition = () => { throw new Error('foo')}
    const report = await m.run({state: 'QOUT'}, 'bar', { event: 'hello'})
    report.user.should.equal('bar')
    report.error.message.should.equal('foo')
    report.error.tag.should.equal('STATE_TRANSITION')
    report.error.state.should.eql({state: 'QOUT'})
  })


  it('returns STATE_ACTIONS error if run throws for unknown reason', async () => {

    const m = new Machine()
    m.transition = () => ({newState: {}, output: {}})
    m.actionsResponses = () => ({})
    m.act = () => Promise.reject(new Error('foo'))

    const report = await m.run({state: 'QOUT'}, 'bar', { event: 'hello'})
    report.user.should.equal('bar')
    report.error.message.should.equal('foo')
    report.error.tag.should.equal('STATE_ACTIONS')
  })

  it('returns specific tag error if run throws MachineIOError', async () => {

    const m = new Machine()
    m.transition = () => ({newState: {}, output: {}})
    m.actionsResponses = () => ({})
    m.act = () => Promise.reject(new MachineIOError('BAZ', 'foo', { code: 'FB' }))

    const report = await m.run({state: 'QOUT'}, 'bar', { event: 'hello'})
    report.user.should.equal('bar')
    report.error.message.should.equal('foo')
    report.error.tag.should.equal('BAZ')
    report.error.code.should.equal('FB')
  })


  it('returns specific tag error if actionsResponses throws MachineIOError', async () => {

    const m = new Machine()
    m.transition = () => ({newState: {}, output: {}})
    m.actionsResponses = () => Promise.reject(new MachineIOError('BAZ', 'foo', { code: 'FB' }))
    m.act = () => ({})

    const report = await m.run({state: 'QOUT'}, 'bar', { event: 'hello'})
    report.user.should.equal('bar')
    report.error.message.should.equal('foo')
    report.error.tag.should.equal('BAZ')
    report.error.code.should.equal('FB')
  })



  it('returns a report with actions if all goes well', async () => {
    const m = new Machine()
    m.transition = () => ({newState: {}, output: {}})
    m.actionsResponses = () => ({ actions: [{foo: 'qux'}]})
    m.act = () => ({})

    const report = await m.run({state: 'QOUT'}, 'bar', { event: 'hello'})
    report.user.should.equal('bar')
    should.not.exist(report.error)
    report.actions[0].should.eql({foo: 'qux'})
  })

})
