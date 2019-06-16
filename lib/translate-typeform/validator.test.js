const mocha = require('mocha')
const chai = require('chai').should()
const mocks = require('./mocks/typeform-form')

const v = require('./validator')

describe('should validate statement with custom reponseMessage', () => {
  const field = {type: 'statement', title: 'foo', ref: 'foo', md: {responseMessage: 'foobarbaz'}}
  const res = v.validator(field)({ foo: 'bar'})
  res.message.should.equal('foobarbaz')
})
