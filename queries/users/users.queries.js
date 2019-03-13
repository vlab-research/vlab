'use strict';

async function all() {
  const { rows } = await this.query(
    'SELECT * FROM messages ORDER BY timestamp ASC',
  );
  return rows;
}

module.exports = {
  name: 'User',
  queries: pool => ({
    all: all.bind(pool),
  }),
};
