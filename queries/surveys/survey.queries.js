'use strict';

const uuid = require('uuid/v4');

async function create({ formid, form, shortcode, userid }) {
  const CREATE_ONE = `INSERT INTO surveys(id, formid, form, shortcode, userid)
       values($1, $2, $3, $4, $5)
       ON CONFLICT(id) DO NOTHING
       RETURNING *`;
  const values = [uuid(), formid, form, shortcode, userid];
  const { rows } = await this.query(CREATE_ONE, values);
  return rows;
}

module.exports = {
  name: 'Survey',
  queries: pool => ({
    create: create.bind(pool),
  }),
};
