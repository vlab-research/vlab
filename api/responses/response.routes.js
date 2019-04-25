const router = require('express').Router();
const controller = require('./response.controller');

router
  .get('/', controller.getAll)
  .get('/:formid/csv', controller.getResponsesCSV);

module.exports = router;
