const router = require('express').Router();
const responses = require('./responses');
const surveys = require('./surveys');
const typeform = require('./typeform');

router
  .use('/responses', responses)
  .use('/surveys', surveys)
  .use('/typeform', typeform);

module.exports = router;
