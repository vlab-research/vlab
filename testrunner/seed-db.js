const fs = require('fs')

async function getUserId(pool) {
  const {rows} = await pool.query('select * from users;')
  return rows[0].id
}

async function pages(pool, userid) {
  // require('@vlab-research/mox').PAGE_ID
  const pageid = '935593143497601';
  const query = `INSERT INTO facebook_pages(pageid, userid) VALUES($1, $2) ON CONFLICT DO NOTHING`
  return pool.query(query, [pageid, userid])
}

async function surveyExists(pool, shortcode) {
  const userid = await getUserId(pool)
  const query = `SELECT id from surveys where userid = $1 and shortcode = $2;`
  const {rows} = await pool.query(query, [userid, shortcode])
  return !!rows && !!rows.length
}

async function insertSurvey(pool, filename, body) {
  const query = `INSERT INTO surveys(created, formid, form, messages, shortcode, userid, title)
       values($1, $2, $3, $4, $5, $6, $7)
       ON CONFLICT(id) DO NOTHING
       RETURNING *`;

  const userid = await getUserId(pool)
  await pages(pool, userid)
  const created = new Date()
  const formid = filename.split('.')[0]

  const exists = await surveyExists(pool, formid)
  if (exists) return

  const values = [created, formid, body, '', formid, userid, ''];
  await pool.query(query, values)
}

async function seed(chatbase) {
  const pool = chatbase.pool
  for (let form of fs.readdirSync('forms')) {
    const body = fs.readFileSync(`forms/${form}`, 'utf8')
    insertSurvey(pool, form, body)
  }
}

module.exports = { seed }
