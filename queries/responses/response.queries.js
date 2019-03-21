'use strict';

async function all() {
  const GET_ALL = `SELECT *
    FROM  (
       SELECT DISTINCT ON (1) userid, timestamp AS first_timestamp, response AS first_response
       FROM   responses
       ORDER  BY 1,2
       ) f
    JOIN (
       SELECT DISTINCT ON (1) userid, timestamp AS last_timestamp, response AS second_response
       FROM   responses
       ORDER  BY 1,2 DESC
       ) l USING (userid)`;
  const { rows } = await this.query(GET_ALL);
  return rows;
}

module.exports = {
  name: 'Response',
  queries: pool => ({
    all: all.bind(pool),
  }),
};
