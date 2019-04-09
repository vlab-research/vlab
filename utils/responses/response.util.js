'use strict';

const stringify = require('csv-stringify');

function toCSV(arr) {
  return stringify(arr, {
    header: true,
  });
}

module.exports = {
  toCSV,
};
