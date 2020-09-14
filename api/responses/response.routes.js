const router = require('express').Router();
const controller = require('./response.controller');

router
  .get('/', controller.getAll)
  .get('/csv', controller.getResponsesCSV);

module.exports = router;
