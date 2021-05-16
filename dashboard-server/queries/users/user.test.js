const { Pool } = require('pg');
require('chai').should();
require('mocha');

const model = require('./user.queries');

const { DATABASE_CONFIG } = require('../../config');

describe('User queries', () => {
  let User;
  let vlabPool;

  before(async () => {
    let pool = new Pool({
      user: 'root',
      host: 'localhost',
      database: 'default',
      password: undefined,
      port: 5432,
    });

    try {
      await pool.query('CREATE DATABASE chatroach');
    } catch (e) {}

    vlabPool = new Pool(DATABASE_CONFIG);

    await vlabPool.query(
      `CREATE TABLE chatroach.users(
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       token VARCHAR NOT NULL,
       email VARCHAR NOT NULL UNIQUE
       );`,
    );
    await vlabPool.query('DELETE FROM users');

    User = model.queries(vlabPool);
  });

  afterEach(async () => {
    await vlabPool.query('DELETE FROM users');
  });

  after(async () => {
    await vlabPool.query('DROP TABLE users CASCADE');
  });

  describe('.create()', () => {
    it('should insert a new user and return the newly created record', async () => {
      const user = {
        token: 'HxpnYoykme73Jz1c9DdAxPws77GzH9jLqE1wu1piSqJj',
        email: 'test@vlab.com',
      };
      const newUser = await User.create(user);
      newUser.token.should.equal(user.token);
      newUser.email.should.equal(user.email);
    });
  });

  describe('.update()', () => {
    it('should update a user or create a new one', async () => {
      const user = {
        token: '8eQ9ZYXw2Vsb16aC7aKzXFqzE7oamzKQttaHnCNHoRu8',
        email: 'test@vlab.com',
      };
      const newUser = await User.update(user);
      newUser.token.should.equal(user.token);
      newUser.email.should.equal(user.email);

      user.token = 'HxpnYoykme73Jz1c9DdAxPws77GzH9jLqE1wu1piSqJj';
      const userUpdated = await User.update(user);
      userUpdated.token.should.equal(user.token);
      userUpdated.email.should.equal(user.email);
    });
  });

  describe('.user()', () => {
    it('should return the corresponding user', async () => {
      const user = {
        token: '8eQ9ZYXw2Vsb16aC7aKzXFqzE7oamzKQttaHnCNHoRu8',
        email: 'test@vlab.com',
      };
      await User.create(user);
      const userFromDb = await User.user(user);
      userFromDb.token.should.equal(user.token);
      userFromDb.email.should.equal(user.email);
    });
  });
});
