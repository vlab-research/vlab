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
       parent_surveyid UUID NOT NULL,
       parent_shortcode INT NOT NULL,
       surveyid UUID NOT NULL,
       shortcode INT NOT NULL,
       flowid INT NOT NULL,
       userid VARCHAR NOT NULL,
       question_ref VARCHAR NOT NULL,
       question_idx INT NOT NULL,
       question_text VARCHAR NOT NULL,
       response VARCHAR NOT NULL,
       seed INT NOT NULL,
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
      const MOCK_QUERY = `INSERT INTO responses(parent_surveyid, parent_shortcode, surveyid, shortcode, flowid, userid, question_ref, question_idx, question_text, response, seed, timestamp)
      VALUES
        ('b8b960ca-3c0d-4a64-a058-2140ee89596b', '101', 'b8b960ca-3c0d-4a64-a058-2140ee89596b', '101', 100001, '124', 'ref', 10, 'text', '{ "text": "last" }', '6789', current_date + interval '14 hour')
       ,('f5de09c8-f2c3-49ac-847d-33c8bf5be427', '202', 'f5de09c8-f2c3-49ac-847d-33c8bf5be427', '202', 100003, '123', 'ref', 10, 'text', '{ "text": "last" }', '6789', date '2019-04-18' + interval '12 hour')
       ,('b8b960ca-3c0d-4a64-a058-2140ee89596b', '101', 'b8b960ca-3c0d-4a64-a058-2140ee89596b', '101', 100004, '124', 'ref', 10, 'text', '{ "text": "first" }', '6789', current_date + interval '10 hour')
       ,('f5de09c8-f2c3-49ac-847d-33c8bf5be427', '202', 'f5de09c8-f2c3-49ac-847d-33c8bf5be427', '202', 100005, '123', 'ref', 10, 'text', '{ "text": "first" }', '6789', date '2019-04-18' + interval '8 hour')
       ,('f5de09c8-f2c3-49ac-847d-33c8bf5be427', '202', 'f5de09c8-f2c3-49ac-847d-33c8bf5be427', '202', 100003, '125', 'ref', 10, 'text', '{ "text": "last" }', '6789', date '2019-04-18' + interval '12 hour')
       ,('b8b960ca-3c0d-4a64-a058-2140ee89596b', '101', 'b8b960ca-3c0d-4a64-a058-2140ee89596b', '101', 100004, '125', 'ref', 10, 'text', '{ "text": "first" }', '6789', date '2019-04-18' + interval '10 hour')
       ,('f5de09c8-f2c3-49ac-847d-33c8bf5be427', '202', 'f5de09c8-f2c3-49ac-847d-33c8bf5be427', '202', 100005, '125', 'ref', 10, 'text', '{ "text": "first" }', '6789', date '2019-04-18' + interval '8 hour')
       ,('b8b960ca-3c0d-4a64-a058-2140ee89596b', '101', 'b8b960ca-3c0d-4a64-a058-2140ee89596b', '101', 100006, '124', 'ref', 10, 'text', '{ "text": "middle" }', '6789', current_date + interval '12 hour')`;

      await vlabPool.query(MOCK_QUERY);
      const responses = await Response.all();

      responses[0].first_response.should.equal('{ "text": "first" }');
      responses[0].last_response.should.equal('{ "text": "last" }');
      responses[0].surveyid.should.equal('f5de09c8-f2c3-49ac-847d-33c8bf5be427');
      responses[1].first_response.should.equal('{ "text": "first" }');
      responses[1].last_response.should.equal('{ "text": "last" }');
      responses[1].surveyid.should.equal('b8b960ca-3c0d-4a64-a058-2140ee89596b');
    });
  });
});
