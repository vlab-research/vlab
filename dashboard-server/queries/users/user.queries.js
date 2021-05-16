'use strict';

async function create({ email }) {
  const CREATE_ONE = `INSERT INTO users(email)
       values($1)
       ON CONFLICT(email) DO NOTHING
       RETURNING *`;
  const values = [email];
  const { rows } = await this.query(CREATE_ONE, values);
  return rows[0];
}


async function user({ email }) {
  const GET = `SELECT * FROM users WHERE email=$1`;
  const { rows } = await this.query(GET, [email]);
  return !!rows.length && rows[0];
}

module.exports = {
  name: 'User',
  queries: pool => ({
    create: create.bind(pool),
    user: user.bind(pool),
  }),
};
