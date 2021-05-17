async function getResponses(chatbase, userid) {
  const {rows} = await chatbase.pool.query('SELECT * FROM responses WHERE userid=$1 ORDER BY timestamp ASC', [userid])
  return rows
}

async function getState(chatbase, userid) {
  const {rows} = await chatbase.pool.query('SELECT * FROM states WHERE userid=$1', [userid])
  return rows[0]
}


module.exports = { getResponses, getState }
