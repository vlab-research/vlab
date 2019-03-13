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
    it('should get all list of messages', async () => {
      const mockMessage = '{ "foo": "bar" }';
      await vlabPool.query(
      'INSERT INTO messages(id, userid, content, timestamp) values($1, $2, $3, $4)',
      [100000, '123', mockMessage, new Date()]
    )
      const messages = await User.all();
      messages[0].content.should.equal('{ "foo": "bar" }');
    });

    it('should return the user as a string', async () => {
      const mockMessage = '{ "foo": "bar" }';
      await vlabPool.query(
      'INSERT INTO messages(id, userid, content, timestamp) values($1, $2, $3, $4)',
      [100000, '123', mockMessage, new Date()]
    )
      const messages = await User.all();
      messages[0].userid.should.equal('123');
    });

    it('should gets multiple messages from one user', async () => {
      const mockMessages = ['{ "foo": "bar" }', '{ "baz": "qux" }'];
      for (let msg of mockMessages) {
        await vlabPool.query(
      'INSERT INTO messages(id, userid, content, timestamp) values($1, $2, $3, $4)',
      [Math.floor(Math.random() * 1000000), '123', msg, new Date()]
    )
      }
      const messages = await User.all();
      messages[0].content.should.equal('{ "foo": "bar" }');
      messages[1].content.should.equal('{ "baz": "qux" }');
    });

    it('rethrows errors on pool error', async () => {
      class TestError extends Error {}
      let error;

      try {
        vlabPool.emit('error', new TestError('foo'));
      } catch (e) {
        error = e;
      }

      error.should.be.instanceof(TestError);
    });
  });
});
