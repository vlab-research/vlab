const u = require('./utils')

const { getStarted, echo, statementEcho, delivery, read, qr, text, multipleChoice, referral} = require('./events.test')


describe('getForm', () => {
  before(() => {
    prevFallback = process.env.FALLBACK_FORM
    process.env.FALLBACK_FORM = 'fallback'
  })
  after(() => {
    process.env.FALLBACK_FORM = prevFallback
  })

  it('gets a form when one exists', () => {
    u.getForm(referral).should.equal('FOO')
  })

  it('gets the fallback form when referral has no form', () => {
    u.getForm({...referral, referral: { ref: 'blah'}}).should.equal('fallback')
  })
})

describe('_group', ()=> {
  it('pairs when even', ()=> {
    u._group([1,2,3,4]).should.deep.equal({1: 2, 3: 4})
    u._group(['foo', 'bar', 'baz', 'buz']).should.deep.equal({foo: 'bar', baz: 'buz'})
  })

  it('leaves last item undefined when odd', ()=> {
    u._group(['foo', 'bar', 'baz']).should.deep.equal({foo: 'bar', baz: undefined})
  })
})

describe('getMetadata', () => {
  it('gets metadata from referral', () => {
    u.getMetadata(referral).should.deep.equal({ form: 'FOO', foo: 'bar', seed: 4001850155 })
  })

  it('fails silently when there is no referral event', () => {
    u.getMetadata(echo).should.deep.equal({})
  })
})
