'use strict';

async function create({ formid, messages, form, shortcode, userid, title }) {
  const CREATE_ONE = `INSERT INTO surveys(formid, form, messages, shortcode, userid, title)
       values($1, $2, $3, $4, $5, $6)
       ON CONFLICT(id) DO NOTHING
       RETURNING *`;
  const values = [formid, form, messages, shortcode, userid, title];
  const { rows } = await this.query(CREATE_ONE, values);
  return rows;
}

async function retrieveByPage({pageid, code}) {
  const RETRIEVE = `SELECT surveys.*
                    FROM surveys
                    LEFT JOIN facebook_pages as face
                    USING (userid)
                    WHERE pageid=$1 AND shortcode=$2`;

  const values = [pageid, code];
  const { rows } = await this.query(RETRIEVE, values);
  return rows;
}

async function retrieve({ email }) {

  const RETRIEVE_ALL = `SELECT surveys.* FROM surveys
                        LEFT JOIN users on surveys.userid = users.id
                        WHERE email=$1`;
  const values = [email];
  const { rows } = await this.query(RETRIEVE_ALL, values);
  return rows;
}

async function includes({ userid, code }) {
  const INCLUDES = `SELECT * FROM surveys WHERE userid=$1 AND shortcode=$2`;
  const { rows } = await this.query(INCLUDES, [userid, code]);
  return !!rows.length;
}

module.exports = {
  name: 'Survey',
  queries: pool => ({
    create: create.bind(pool),
    retrieve: retrieve.bind(pool),
    retrieveByPage: retrieveByPage.bind(pool),
    includes: includes.bind(pool),
  }),
};
