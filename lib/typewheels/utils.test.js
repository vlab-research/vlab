const u = require('./utils')

const { getStarted, echo, statementEcho, delivery, read, qr, text, multipleChoice, referral} = require('./events.test')

describe('recursiveJSONParser', () => {
  it('works super duper well', () => {
    u.recursiveJSONParser({}).should.deep.equal({})

    u.recursiveJSONParser({ foo: 'bar'}).should.deep.equal({ foo: 'bar'})

    u.recursiveJSONParser({ foo: null}).should.deep.equal({ foo: null})

    u.recursiveJSONParser({ foo: '{ "foo": "bar"}'})
      .should.deep.equal({ foo: { foo: 'bar' }})

    u.recursiveJSONParser([{ foo: '{ "foo": "bar"}'}, null])
      .should.deep.equal([{ foo: { foo: 'bar' }}, null])

    u.recursiveJSONParser(JSON.stringify([JSON.stringify({ foo: JSON.stringify({ foo: 'bar'})}), null]))
      .should.deep.equal([{ foo: { foo: 'bar' }}, null])
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
    u.getMetadata([referral, echo, read]).should.deep.equal({ form: 'FOO', foo: 'bar'})
  })

  it('fails silently when there is no referral event', () => {
    u.getMetadata([echo, read]).should.deep.equal({})
  })
})


describe('splitLogsByForm', () => {
  before(() => {
    prevFallback = process.env.FALLBACK_FORM
    process.env.FALLBACK_FORM = 'fallback'
  })
  after(() => {
    process.env.FALLBACK_FORM = prevFallback
  })

  it('works with an empty log', () => {
    u.splitLogsByForm(u.parseLogJSON([])).should.deep.equal([])
  })

  it('works with a log with no form', () => {
    u.splitLogsByForm(u.parseLogJSON([text])).should.deep.equal([['fallback', [text]]])
  })


  it('Works after starting with not-a-form', () => {
    const log = [text, statementEcho, getStarted, delivery, read]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split[1][0].should.equal('FOO')
  })

  it('Works when starting via get started', () => {
    const log = [getStarted]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split.should.deep.equal([['FOO', [getStarted]]])
  })

  it('splits well with different referrals', () => {
    const ref2 = {...referral, referral: {...referral.referral, ref: 'form.BAR'}}
    const log = [referral, text, echo, delivery, read, ref2]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split[0][1].length.should.equal(5)
    split[1][1].length.should.equal(1)
  })

  it('Ignores additional referrals for the same form ', () => {
    const log = [referral, text, echo, delivery, read, multipleChoice, referral, echo]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split.length.should.equal(1)
    split[0][1].length.should.equal(8)
  })

  it('Works when returning to old form', () => {
    const ref2 = {...referral, referral: {...referral.referral, ref: 'form.BAR'}}
    const log = [referral, text, echo, delivery, ref2, read, multipleChoice, referral, echo]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split.length.should.equal(3)
    split[0][1].length.should.equal(4)
    split[1][1].length.should.equal(3)
    split[2][1].length.should.equal(2)
  })
})
