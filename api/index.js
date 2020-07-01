const router = require('express').Router();
const responses = require('./responses');
const surveys = require('./surveys');
const typeform = require('./typeform');
const facebook = require('./facebook');

router
  .use('/responses', responses)
  .use('/surveys', surveys)
  .use('/typeform', typeform)
  .use('/facebook', facebook);


module.exports = router;
