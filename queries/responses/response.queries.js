'use strict';

async function all() {
  const GET_ALL = `SELECT *
    FROM  (
       SELECT DISTINCT ON (1) userid, timestamp AS first_timestamp, response AS first_response, formid
       FROM   responses
       ORDER  BY 1,2
       ) f
    JOIN (
       SELECT DISTINCT ON (1) userid, timestamp AS last_timestamp, response AS last_response, formid
       FROM   responses
       ORDER  BY 1,2 DESC
       ) l USING (userid)`;
  const { rows } = await this.query(GET_ALL);
  return rows;
}

async function formResponses(formid) {
  const GET_FORM_RESPONSES = `SELECT * FROM responses WHERE formid=$1 ORDER BY timestamp DESC`;
  const { rows } = await this.query(GET_FORM_RESPONSES, [formid]);
  return rows;
}

module.exports = {
  name: 'Response',
  queries: pool => ({
    all: all.bind(pool),
    formResponses: formResponses.bind(pool),
  }),
};
