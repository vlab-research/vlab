async function get ({email}) {
   const q = `
     WITH t AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY entity, key ORDER BY created DESC) AS n
                FROM credentials
                JOIN users ON userid=id
                WHERE email = $1)
     SELECT entity, key, details, created
     FROM t
     WHERE n = 1
  `

  const values = [email]
  const {rows} = await this.query(q, values)
  return rows
}

async function getOne ({email, entity, key}) {
   const q = `
     SELECT entity, key, details, created
     FROM credentials
     JOIN users ON userid=id
     WHERE email = $1
     AND entity = $2
     AND key = $3
     ORDER BY created DESC
     LIMIT 1
  `

  const values = [email, entity, key]
  const {rows} = await this.query(q, values)
  return rows[0]
}

// TURN INTO UPSERT?
async function update ({entity, key, details, email}) {
  const q = `
    UPDATE credentials
    SET (details, created) = ($4, CURRENT_TIMESTAMP)
    WHERE entity = $1
    AND key = $2
    AND userid = (SELECT id FROM users WHERE email = $3)
    RETURNING *
  `

  const values = [entity, key, email, details]
  const {rows} = await this.query(q, values)
  return rows[0]
}



async function create ({entity, key, details, email}) {

  const q = `
    INSERT INTO credentials (entity, key, details, userid)
    VALUES ($1, $2, $3, (SELECT id FROM users WHERE email = $4))
    RETURNING *
  `

  const values = [entity, key, details, email]
  const {rows} = await this.query(q, values)
  return rows[0]
}


module.exports = {
  name: 'Credential',
  queries: pool => ({
    create: create.bind(pool),
    update: update.bind(pool),
    get: get.bind(pool),
    getOne: getOne.bind(pool),
  }),
};
