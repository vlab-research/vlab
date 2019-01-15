const u = require('./utils')

const { getStarted, echo, delivery, read, qr, text, multipleChoice, referral} = require('./events.test')

describe('recursiveJSONParser', () => {
  it('works super duper well', () => {
    u.recursiveJSONParser({}).should.deep.equal({})

    u.recursiveJSONParser({ foo: 'bar'}).should.deep.equal({ foo: 'bar'})

    u.recursiveJSONParser({ foo: null}).should.deep.equal({ foo: null})

    u.recursiveJSONParser({ foo: '{ "foo": "bar"}'})
      .should.deep.equal({ foo: { foo: 'bar' }})

    u.recursiveJSONParser([{ foo: '{ "foo": "bar"}'}, null])
      .should.deep.equal([{ foo: { foo: 'bar' }}, null])
  })
})


describe('splitLogsByForm', () => {
  it('works with an empty log', () => {
    u.splitLogsByForm(u.parseLogJSON([])).should.deep.equal([])
  })

  it('works with a log with no form', () => {
    u.splitLogsByForm(u.parseLogJSON([text])).should.deep.equal([])
  })

  it('Works when starting via get started', () => {
    const log = [getStarted]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split.should.deep.equal([['FOO', []]])
  })

  it('splits well with different referrals', () => {
    const ref2 = {...referral, referral: {...referral.referral, ref: 'BAR.something'}}
    const log = [referral, text, echo, delivery, read, multipleChoice, ref2, echo]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split[0][1].length.should.equal(5)
    split[1][1].length.should.equal(1)
  })

  it('Ignores additional referrals for the same form ', () => {
    const log = [referral, text, echo, delivery, read, multipleChoice, referral, echo]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split.length.should.equal(1)
    split[0][1].length.should.equal(6)
  })

  it('Works when returning to old form', () => {
    const ref2 = {...referral, referral: {...referral.referral, ref: 'BAR.something'}}
    const log = [referral, text, echo, delivery, ref2, read, multipleChoice, referral, echo]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split.length.should.equal(3)
    split[0][1].length.should.equal(3)
    split[1][1].length.should.equal(2)
    split[2][1].length.should.equal(1)
  })

  it('Works when starting via get started', () => {
    const log = [getStarted]
    const split = u.splitLogsByForm(u.parseLogJSON(log))
    split.should.deep.equal([['FOO', []]])
  })
})
