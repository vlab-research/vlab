'use strict';

async function create({
  created,
  formid,
  form,
  messages,
  shortcode,
  userid,
  title,
}) {
  const CREATE_ONE = `INSERT INTO surveys(created, formid, form, messages, shortcode, userid, title)
       values($1, $2, $3, $4, $5, $6, $7)
       ON CONFLICT(id) DO NOTHING
       RETURNING *`;
  const values = [created, formid, form, messages, shortcode, userid, title];
  const { rows } = await this.query(CREATE_ONE, values);
  return rows[0];
}

async function retrieveByPage({ pageid, code, timestamp }) {
  const RETRIEVE = `SELECT surveys.*
                    FROM surveys
                    LEFT JOIN facebook_pages as face
                    USING (userid)
                    WHERE pageid=$1 AND shortcode=$2 AND created<=$3
                    ORDER BY created DESC`;

  const created = new Date(+timestamp)
  const values = [pageid, code, created];
  const { rows } = await this.query(RETRIEVE, values);
  return rows;
}

async function retrieve({ email }) {
  const RETRIEVE_ALL = `SELECT surveys.* FROM surveys
                        LEFT JOIN users on surveys.userid = users.id
                        WHERE email=$1
                        ORDER BY created DESC`;
  const values = [email];
  const { rows } = await this.query(RETRIEVE_ALL, values);
  return rows;
}

module.exports = {
  name: 'Survey',
  queries: pool => ({
    create: create.bind(pool),
    retrieve: retrieve.bind(pool),
    retrieveByPage: retrieveByPage.bind(pool),
  }),
};
