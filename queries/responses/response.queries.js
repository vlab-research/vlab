'use strict';

const QueryStream = require('pg-query-stream')

async function all() {
  const GET_ALL = `SELECT *
    FROM  (
       SELECT DISTINCT ON (1) userid, timestamp AS first_timestamp, response AS first_response, surveyid
       FROM   responses
       ORDER  BY 1,2
       ) f
    JOIN (
       SELECT DISTINCT ON (1) userid, timestamp AS last_timestamp, response AS last_response, surveyid
       FROM   responses
       ORDER  BY 1,2 DESC
       ) l USING (userid)`;
  const { rows } = await this.query(GET_ALL);
  return rows;
}

async function formResponses(survey) {
  const query = new QueryStream(`SELECT responses.* FROM responses  LEFT JOIN surveys ON responses.surveyid = surveys.id WHERE surveys.survey_name=$1 ORDER BY timestamp DESC`, [survey])

  const client = await this.connect();
  const stream = client.query(query);
  return stream;
}

module.exports = {
  name: 'Response',
  queries: pool => ({
    all: all.bind(pool),
    formResponses: formResponses.bind(pool),
  }),
};
