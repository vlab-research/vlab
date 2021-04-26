'use strict';

const  { DBStream } = require('./pgstream')

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

async function responsesQuery(pool, name, lim) {

  const query = `SELECT parent_surveyid,
                        parent_shortcode,
                        surveyid,
                        responses.shortcode,
                        flowid,
                        responses.userid,
                        question_ref,
                        question_idx,
                        question_text,
                        response,
                        timestamp,
                        responses.metadata,
                        pageid,
                        translated_response
                 FROM responses
                 LEFT JOIN surveys ON responses.surveyid = surveys.id
                 WHERE surveys.survey_name=$1 AND (responses.userid, timestamp, question_ref) > ($2, $3, $4)
                 ORDER BY (responses.userid, timestamp, question_ref)
                 LIMIT 100000`

  const res = await pool.query(query, [name, ...lim])
  const fin = res.rows.slice(-1)[0]

  if (!fin) return [null, null]

  return [res.rows, [fin['userid'], fin['timestamp'], fin['question_ref']]]
}

async function formResponses(survey) {
  const fn = (lim) => responsesQuery(this, survey, lim)
  const stream = new DBStream(fn, ['', new Date('1970-01-01'), ''])
  return stream;
}

module.exports = {
  name: 'Response',
  queries: pool => ({
    all: all.bind(pool),
    formResponses: formResponses.bind(pool),
  }),
};
