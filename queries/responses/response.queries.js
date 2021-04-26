'use strict';

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
  const GET_FORM_RESPONSES = `SELECT responses.* FROM responses  LEFT JOIN surveys ON responses.surveyid = surveys.id WHERE surveys.survey_name=$1 ORDER BY timestamp DESC`;
  const { rows } = await this.query(GET_FORM_RESPONSES, [survey]);
  return rows;
}

module.exports = {
  name: 'Response',
  queries: pool => ({
    all: all.bind(pool),
    formResponses: formResponses.bind(pool),
  }),
};
