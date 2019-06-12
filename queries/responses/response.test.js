const { Pool } = require('pg');
require('chai').should();
require('mocha');

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
      await pool.query('CREATE DATABASE vlab_dashboard_test');
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
       ,('form2', 100003, '123', 'ref', 10, 'text', '{ "text": "last" }', date '2019-04-18' + interval '12 hour')
       ,('form1', 100004, '124', 'ref', 10, 'text', '{ "text": "first" }', current_date + interval '10 hour')
       ,('form2', 100005, '123', 'ref', 10, 'text', '{ "text": "first" }', date '2019-04-18' + interval '8 hour')
       ,('form2', 100003, '125', 'ref', 10, 'text', '{ "text": "last" }', date '2019-04-18' + interval '12 hour')
       ,('form1', 100004, '125', 'ref', 10, 'text', '{ "text": "first" }', date '2019-04-18' + interval '10 hour')
       ,('form2', 100005, '125', 'ref', 10, 'text', '{ "text": "first" }', date '2019-04-18' + interval '8 hour')
       ,('form1', 100006, '124', 'ref', 10, 'text', '{ "text": "middle" }', current_date + interval '12 hour')`;
      await vlabPool.query(MOCK_QUERY);
      const responses = await Response.all();
      responses[0].first_response.should.equal('{ "text": "first" }');
      responses[0].last_response.should.equal('{ "text": "last" }');
      responses[0].formid.should.equal('form2');
      responses[1].first_response.should.equal('{ "text": "first" }');
      responses[1].last_response.should.equal('{ "text": "last" }');
      responses[1].formid.should.equal('form1');
    });
  });

  describe('.formResponses()', () => {
    it('should return all the responses by formid', async () => {
      const MOCK_QUERY = `INSERT INTO responses(formid, flowid, userid, question_ref, question_idx, question_text, response, timestamp) 
      VALUES
        ('form1', 100001, '124', 'ref', 10, 'text', '{ "text": "last" }', current_date + interval '14 hour')
       ,('form2', 100003, '123', 'ref', 10, 'text', '{ "text": "last" }', current_date + interval '12 hour')
       ,('form3', 100004, '124', 'ref', 10, 'text', '{ "text": "first" }', current_date + interval '10 hour')
       ,('form1', 100005, '123', 'ref', 10, 'text', '{ "text": "first" }', current_date + interval '8 hour')
       ,('form1', 100006, '124', 'ref', 10, 'text', '{ "text": "middle" }', current_date + interval '12 hour')`;
      await vlabPool.query(MOCK_QUERY);
      const responses = await Response.formResponses('form1');
      responses[0].response.should.equal('{ "text": "last" }');
      responses[0].flowid.should.equal(100001);
      responses[1].response.should.equal('{ "text": "middle" }');
      responses[1].flowid.should.equal(100006);
      responses[2].response.should.equal('{ "text": "first" }');
      responses[2].flowid.should.equal(100005);
    });
  });
});
