const { Pool } = require('pg')
const fs = require('fs')

let pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_DATABASE,
  password: process.env.DB_PASSWORD,
  port: process.env.DB_PORT,
})

async function getUserId() {
  const {rows} = await pool.query('select * from users;')
  return rows[0].id
}

async function pages(userid) {
  // require('@vlab-research/mox').PAGE_ID
  const pageid = '935593143497601';
  const query = `INSERT INTO facebook_pages(pageid, userid) VALUES($1, $2) ON CONFLICT DO NOTHING`
  return pool.query(query, [pageid, userid])
}

async function insertSurvey(filename, body) {
  const query = `INSERT INTO surveys(created, formid, form, messages, shortcode, userid, title)
       values($1, $2, $3, $4, $5, $6, $7)
       ON CONFLICT(id) DO NOTHING
       RETURNING *`;

  const userid = await getUserId()
  await pages(userid)
  const created = new Date()
  const formid = filename.split('.')[0]
  const values = [created, formid, body, '', formid, userid, ''];
  await pool.query(query, values)
}

async function seed() {
  for (let form of fs.readdirSync('forms')) {
    const body = fs.readFileSync(`forms/${form}`, 'utf8')
    insertSurvey(form, body)
  }
}

module.exports = { seed }
