const { Pool } = require('pg');
const chai = require('chai');
const mocha = require('mocha'); // eslint-disable-line no-unused-vars
const should = chai.should(); // eslint-disable-line no-unused-vars

const model = require('./response.queries');

const { DATABASE_CONFIG } = require('../../config');

describe('Response queries', () => {
  let Response;
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
      `CREATE TABLE responses(
       formid VARCHAR NOT NULL,
       flowid INT NOT NULL,
       userid VARCHAR NOT NULL,
       question_ref VARCHAR NOT NULL,
       question_idx INT NOT NULL,
       question_text VARCHAR NOT NULL,
       response VARCHAR NOT NULL,
       timestamp TIMESTAMPTZ NOT NULL,
       PRIMARY KEY (userid, timestamp)
      )`,
    );
    await vlabPool.query('DELETE FROM responses');

    Response = model.queries(vlabPool);
  });

  afterEach(async () => {
    await vlabPool.query('DELETE FROM responses');
  });

  after(async () => {
    await vlabPool.query('DROP TABLE responses');
  });

  describe('.all()', () => {
    it('should get the list of the first and last responses for each user', async () => {
      const MOCK_QUERY = `INSERT INTO responses(formid, flowid, userid, question_ref, question_idx, question_text, response, timestamp) 
      VALUES
        ('form1', 100001, '124', 'ref', 10, 'text', '{ "text": "last" }', current_date + interval '14 hour')
       ,('form2', 100003, '123', 'ref', 10, 'text', '{ "text": "last" }', current_date + interval '12 hour')
       ,('form3', 100004, '124', 'ref', 10, 'text', '{ "text": "first" }', current_date + interval '10 hour')
       ,('form4', 100005, '123', 'ref', 10, 'text', '{ "text": "first" }', current_date + interval '8 hour')
       ,('form5', 100006, '124', 'ref', 10, 'text', '{ "text": "middle" }', current_date + interval '12 hour')`;
      await vlabPool.query(MOCK_QUERY);
      const responses = await Response.all();
      responses[0].first_response.should.equal('{ "text": "first" }');
      responses[0].second_response.should.equal('{ "text": "last" }');
      responses[1].first_response.should.equal('{ "text": "first" }');
      responses[1].second_response.should.equal('{ "text": "last" }');
    });
  });
});
