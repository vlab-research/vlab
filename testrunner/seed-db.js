const fs = require('fs')

async function getUserId(pool) {
  const {rows} = await pool.query(`INSERT INTO users(token, email) VALUES($1, $2) ON CONFLICT(email) DO UPDATE SET token = $1 RETURNING id;`, ['test', 'test@test.com'])
  return rows[0].id
}

async function pages(pool, userid) {
  // require('@vlab-research/mox').PAGE_ID
  const pageid = '935593143497601';
  const token = 'test'
  const query = `INSERT INTO facebook_pages(pageid, userid, token) VALUES($1, $2, $3) ON CONFLICT(pageid) DO NOTHING`
  return pool.query(query, [pageid, userid, token])
}

async function surveyExists(pool, userid, shortcode) {
  const query = `SELECT id from surveys where userid = $1 and shortcode = $2;`
  const {rows} = await pool.query(query, [userid, shortcode])
  return !!rows && !!rows.length
}

async function insertSurvey(pool, filename, body, userid) {
  const query = `INSERT INTO surveys(created, formid, form, messages, shortcode, userid, title, translation_conf)
       values($1, $2, $3, $4, $5, $6, $7, $8)
       RETURNING *`;

  const form = JSON.parse(body)
  const messages = form.custom_messages || {}
  const created = new Date()
  const formid = filename.split('.')[0]

  const exists = await surveyExists(pool, userid, formid)
  if (exists) return

  const values = [created, formid, JSON.stringify(form), JSON.stringify(messages), formid, userid, '', {}];
  await pool.query(query, values)
}

function readForm(form) {
  return [form, fs.readFileSync(`forms/${form}`, 'utf8')]
}

async function seed(chatbase) {
  const pool = chatbase.pool

  const userId = await getUserId(pool)
  await pages(pool, userId)

  const inserts = fs.readdirSync('forms')
    .map(readForm)
    .map(([form, body]) => insertSurvey(pool, form, body, userId))

  return Promise.all(inserts).catch(err => {
    console.error(err)
  })
}

module.exports = { seed }
