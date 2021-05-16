const router = require('express').Router();

router
  .use('/responses', require('./responses'))
  .use('/users', require('./users'))
  .use('/surveys', require('./surveys'))
  .use('/typeform', require('./typeform'))
  .use('/credentials', require('./credentials'))
  .use('/facebook', require('./facebook'));

module.exports = router;
