const { Pool } = require('pg');
const chai = require('chai');
const mocha = require('mocha'); // eslint-disable-line no-unused-vars
const should = chai.should(); // eslint-disable-line no-unused-vars

const model = require('./users.queries');

process.env.NODE_ENV = 'test';

const { DATABASE_CONFIG } = require('../../config');

describe('User queries', () => {
  let User;
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
      'CREATE TABLE IF NOT EXISTS messages(id BIGINT PRIMARY KEY, content VARCHAR NOT NULL, userid VARCHAR NOT NULL, timestamp TIMESTAMPTZ)',
    );
    await vlabPool.query('DELETE FROM messages');

    User = model.queries(vlabPool);
  });

  afterEach(async () => {
    await vlabPool.query('DELETE FROM messages');
  });

  after(async () => {
    await vlabPool.query('DROP TABLE messages');
  });

  describe('.all()', () => {
    it('should get all list of user with the first and last message', async () => {
      const MOCK_QUERY = `INSERT INTO messages(id, userid, content, timestamp) 
      VALUES
        (100001, '124', '{ "text": "last" }', current_date + interval '14 hour')
       ,(100003, '123', '{ "text": "last" }', current_date + interval '12 hour')
       ,(100004, '124', '{ "text": "first" }', current_date + interval '10 hour')
       ,(100005, '123', '{ "text": "first" }', current_date + interval '8 hour')
       ,(100006, '124', '{ "text": "middle" }', current_date + interval '12 hour')`;
      await vlabPool.query(MOCK_QUERY);
      const messages = await User.all();
      messages[0].first_message.should.equal('{ "text": "first" }');
      messages[0].second_message.should.equal('{ "text": "last" }');
      messages[1].first_message.should.equal('{ "text": "first" }');
      messages[1].second_message.should.equal('{ "text": "last" }');
    });
  });
});
