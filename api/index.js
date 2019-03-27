const router = require('express').Router();
const responses = require('./responses/response.routes');

router.use('/responses', responses);

module.exports = router;
