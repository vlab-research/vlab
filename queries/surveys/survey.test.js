const { Pool } = require('pg');
const chai = require('chai');
const mocha = require('mocha'); // eslint-disable-line no-unused-vars
const should = chai.should(); // eslint-disable-line no-unused-vars

const model = require('./survey.queries');

const { DATABASE_CONFIG } = require('../../config');

describe('Survey queries', () => {
  let Survey;
  let vlabPool;

  before(async () => {
    let pool = new Pool({
      user: 'postgres',
      host: 'localhost',
      database: 'postgres',
      password: undefined,
      port: 5432,
    });

    try {
      await pool.query('CREATE DATABASE vlab_dashboard');
    } catch (e) {}

    vlabPool = new Pool(DATABASE_CONFIG);

    await vlabPool.query(
      `CREATE TABLE surveys(
       id VARCHAR NOT NULL PRIMARY KEY,
       formid VARCHAR NOT NULL,
       form VARCHAR NOT NULL,
       shortcode INT NOT NULL,
       userid VARCHAR NOT NULL
      )`,
    );
    await vlabPool.query('DELETE FROM surveys');

    Survey = model.queries(vlabPool);
  });

  afterEach(async () => {
    await vlabPool.query('DELETE FROM surveys');
  });

  after(async () => {
    await vlabPool.query('DROP TABLE surveys');
  });

  describe('.create()', () => {
    it('should insert a new survey and return the newly created record', async () => {
      const survey = {
        formid: 'formid-test',
        form: '{"form": "form detail"}',
        shortcode: 1234,
        userid: 'test@vlab.com',
      };
      const newSurvey = await Survey.create(survey);
      newSurvey[0].formid.should.equal('formid-test');
      newSurvey[0].form.should.equal('{"form": "form detail"}');
      newSurvey[0].shortcode.should.equal(1234);
      newSurvey[0].userid.should.equal('test@vlab.com');
    });
  });
});
