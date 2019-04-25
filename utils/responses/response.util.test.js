const chai = require('chai');
const mocha = require('mocha'); // eslint-disable-line no-unused-vars
const should = chai.should(); // eslint-disable-line no-unused-vars

const util = require('./response.util');

describe('Response utils', () => {
  describe('.toCSV()', () => {
    it('should return a csv stream from an array', () => {
      let result = '';
      const input = [
        { form: 1, text: 'test1' },
        { form: 2, text: 'test2' },
        { form: 3, text: 'test3' },
      ];

      const stream = util.toCSV(input);
      stream.on('data', data => {
        result += data.toString();
      });
      stream.on('end', () => {
        result.should.equal('form,text\n1,test1\n2,test2\n3,test3\n');
      });
    });
  });
});
