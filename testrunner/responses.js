async function getResponses(chatbase, userid) {
  const {rows} = await chatbase.pool.query('SELECT * FROM responses WHERE userid=$1 ORDER BY timestamp ASC', [userid])
  return rows
}


module.exports = { getResponses }
