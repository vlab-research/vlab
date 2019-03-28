'use strict';

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

const { DATABASE_CONFIG } = require('../config');

const db = {};

// Connect to the database through ENV config
const pool = new Pool(DATABASE_CONFIG);

pool.on('error', err => {
  throw err;
});

const isDirectory = path => fs.lstatSync(path).isDirectory();

// Read all the models in the folder and generate an available set of queries
fs.readdirSync(__dirname)
  .map(name => path.join(__dirname, name))
  .filter(isDirectory)
  .forEach(dir => {
    const model = require(dir);
    db[model.name] = model.queries(pool);
  });

db.pool = pool;

module.exports = db;
