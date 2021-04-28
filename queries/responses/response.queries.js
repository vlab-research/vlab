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

// TODO: remove question_text and push to another download? save space.
async function responsesQuery(pool, email, name, lim) {

  const query = `SELECT parent_surveyid,
                        parent_shortcode,
                        surveyid,
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
                 LEFT JOIN users ON surveys.userid = users.id
                 WHERE users.email = $1
                 AND surveys.survey_name = $2
                 AND (responses.userid, timestamp, question_ref) > ($3, $4, $5)
                 ORDER BY (responses.userid, timestamp, question_ref)
                 LIMIT 100000`

  const res = await pool.query(query, [email, name, ...lim])
  const fin = res.rows.slice(-1)[0]

  if (!fin) return [null, null]

  return [res.rows, [fin['userid'], fin['timestamp'], fin['question_ref']]]
}

async function formResponses(email, survey) {
  const fn = (lim) => responsesQuery(this, email, survey, lim)
  const stream = new DBStream(fn, ['', new Date('1970-01-01'), ''])
  return stream;
}


async function formData(email, survey) {

  // Adds "version" following same logic as per dashboard.
  // TODO: clean this up, there is duplicated logic with surveys
  // controller -- make surveys controller get by survey_name instead
  // of all surveys? hrm...
  const query = `WITH t AS (
                   SELECT surveys.*, row_number() OVER (partition BY shortcode ORDER BY created) AS version
                   FROM surveys
                   LEFT JOIN users ON surveys.userid = users.id
                   WHERE users.email = $1
                   AND survey_name = $2
                 )
                 SELECT id, shortcode, version, created, metadata, translation_conf
                 FROM t
                 ORDER BY shortcode, created`;

  const { rows } = await this.query(query, [email, survey]);
  return rows;
}

module.exports = {
  name: 'Response',
  queries: pool => ({
    all: all.bind(pool),
    formResponses: formResponses.bind(pool),
    formData: formData.bind(pool),
  }),
};
