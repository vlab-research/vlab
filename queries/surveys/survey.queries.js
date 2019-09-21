'use strict';

const uuid = require('uuid/v4');

async function create ({ formid, messages, form, shortcode, userid, title }) {
  const CREATE_ONE = `INSERT INTO surveys(id, formid, form, messages, shortcode, userid, title)
       values($1, $2, $3, $4, $5, $6, $7)
       ON CONFLICT(id) DO NOTHING
       RETURNING *`;
  const values = [uuid(), formid, form, messages, shortcode, userid, title];
  const { rows } = await this.query(CREATE_ONE, values);
  return rows;
}

async function retrieve ({ userid }) {
  const RETRIEVE_ALL = `SELECT * FROM surveys WHERE userid=$1`;
  const values = [ userid ];
  const { rows } = await this.query(RETRIEVE_ALL, values);
  return rows;
}

async function includes ({ userid, code }) {
  const INCLUDES = `SELECT * FROM surveys WHERE userid=$1 AND shortcode=$2`;
  const { rows } = await this.query(INCLUDES, [userid, code]);
  return !!rows.length;
}

module.exports = {
  name: 'Survey',
  queries: pool => ({
    create: create.bind(pool),
    retrieve: retrieve.bind(pool),
    includes: includes.bind(pool),
  }),
};
