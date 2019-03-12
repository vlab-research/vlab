'use strict';

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

const basename = path.basename(__filename);
const { DATABASE_CONFIG } = require('../config');

const db = {};

// Connect to the database through ENV config
const pool = new Pool(DATABASE_CONFIG);
pool.on('error', err => {
  throw err;
});

// Read all the models in the folder and generate an available set of queries
fs.readdirSync(__dirname)
  .filter(
    file =>
      file.indexOf('.') !== 0 && file !== basename && file.slice(-3) === '.js',
  )
  .forEach(file => {
    const model = require(path.join(__dirname, file));
    db[model.name] = model.queries(pool);
  });

db.pool = pool;

module.exports = db;
