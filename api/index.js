const router = require('express').Router();
const responses = require('./responses');
const surveys = require('./surveys');
const typeform = require('./typeform');
const credentials = require('./credentials');
const facebook = require('./facebook');

router
  .use('/responses', responses)
  .use('/surveys', surveys)
  .use('/typeform', typeform)
  .use('/credentials', credentials)
  .use('/facebook', facebook);


module.exports = router;
