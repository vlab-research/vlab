async function get ({email}) {
   const q = `
   WITH t AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY entity, key ORDER BY created DESC) AS n
              FROM credentials
              JOIN users ON userid=id
              WHERE email = $1)
  SELECT entity, details, created
  FROM t
  WHERE n = 1
  `

  const values = [email]
  const {rows} = await this.query(q, values)
  return rows
}


async function create ({entity, key, details, email}) {
  const q = `
  INSERT INTO credentials (entity, key, details, userid)
  VALUES ($1, $2, $3, (SELECT id FROM users WHERE email = $3))
  RETURNING *
  `

  const values = [entity, key, details, email]
  const {rows} = await this.query(q, values)
  return rows
}


module.exports = {
  name: 'Credential',
  queries: pool => ({
    create: create.bind(pool),
    get: get.bind(pool),
  }),
};
