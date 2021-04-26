'use strict';

const stringify = require('csv-stringify');

// pipe into this
function toCSV() {
  const s = stringify({
    header: true,
  });

  return s
}

module.exports = {
  toCSV,
};
