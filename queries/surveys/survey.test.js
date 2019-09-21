/* eslint-disable no-unused-expressions */
const { Pool } = require('pg');
require('chai').should();
require('mocha');

const surveyModel = require('./survey.queries');
const userModel = require('../users/user.queries');

const { DATABASE_CONFIG } = require('../../config');

describe('Survey queries', () => {
  let Survey;
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
      await pool.query('CREATE DATABASE vlab_dashboard_test');
    } catch (e) {}

    vlabPool = new Pool(DATABASE_CONFIG);

    await vlabPool.query(
      `CREATE TABLE users(
       id VARCHAR NOT NULL PRIMARY KEY,
       token VARCHAR NOT NULL,
       email VARCHAR NOT NULL UNIQUE
      )`,
    );
    await vlabPool.query('DELETE FROM users');

    await vlabPool.query(
      `CREATE TABLE surveys(
       id VARCHAR NOT NULL PRIMARY KEY,
       formid VARCHAR NOT NULL,
       form VARCHAR NOT NULL,
       shortcode INT NOT NULL,
       title VARCHAR NOT NULL,
       userid VARCHAR NOT NULL,
       FOREIGN KEY ("userid") REFERENCES users("email") ON DELETE CASCADE
      )`,
    );
    await vlabPool.query('DELETE FROM surveys');

    User = userModel.queries(vlabPool);
    Survey = surveyModel.queries(vlabPool);
  });

  after(async () => {
    await vlabPool.query('DROP TABLE users CASCADE');
    await vlabPool.query('DROP TABLE surveys');
  });

  describe('.create()', () => {
    it('should insert a new survey and return the newly created record', async () => {
      const user = {
        token: 'HxpnYoykme73Jz1c9DdAxPws77GzH9jLqE1wu1piSqJj',
        email: 'test@vlab.com',
      };
      const newUser = await User.create(user);
      newUser[0].token.should.equal(user.token);
      newUser[0].email.should.equal(user.email);

      const survey = {
        formid: 'S8yR4',
        form: '{"form": "form detail"}',
        shortcode: 123,
        userid: 'test@vlab.com',
        title: 'New User Title',
      };
      const newSurvey = await Survey.create(survey);
      newSurvey[0].formid.should.equal('S8yR4');
      newSurvey[0].form.should.equal('{"form": "form detail"}');
      newSurvey[0].shortcode.should.equal(123);
      newSurvey[0].userid.should.equal('test@vlab.com');
      newSurvey[0].title.should.equal('New User Title');
    });
  });

  describe('.retrieve()', () => {
    it('should insert a new survey and return the newly created record', async () => {
      const user2 = {
        token: 'dasfYoykme73Jz1c93d1xPws77GzuhNU0f1wu1pHeh91',
        email: 'test2@vlab.com',
      };
      await User.create(user2);

      const survey = {
        formid: 'biy23',
        form: '{"form": "form detail"}',
        shortcode: 231,
        userid: 'test@vlab.com',
        title: 'Second Survey',
      };
      await Survey.create(survey);

      const survey2 = {
        formid: '3hu23',
        form: '{"form": "form detail"}',
        shortcode: 123,
        userid: 'test2@vlab.com',
        title: 'Other survey',
      };
      await Survey.create(survey2);

      const userid = 'test@vlab.com';
      const rows = await Survey.retrieve({ userid });
      rows.length.should.be.equal(2);
    });
  });

  describe('.includes()', () => {
    it('should return true on existing code', async () => {
      const [userid, code] = ['test@vlab.com', 123];
      const include = await Survey.includes({ userid, code });
      include.should.be.equal(true);
    });

    it('should return false if code don t exists', async () => {
      const [userid, code] = ['test@vlab.com', 321];
      const include = await Survey.includes({ userid, code });
      include.should.be.equal(false);
    });
  });
});
