'use strict';

async function all() {
  const GET_ALL = `SELECT *
    FROM  (
       SELECT DISTINCT ON (1) userid, timestamp AS first_timestamp, content AS first_message
       FROM   messages
       ORDER  BY 1,2
       ) f
    JOIN (
       SELECT DISTINCT ON (1) userid, timestamp AS last_timestamp, content AS second_message
       FROM   messages
       ORDER  BY 1,2 DESC
       ) l USING (userid)`;
  const { rows } = await this.query(GET_ALL);
  return rows;
}

module.exports = {
  name: 'User',
  queries: pool => ({
    all: all.bind(pool),
  }),
};
