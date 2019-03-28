const router = require('express').Router();
const responses = require('./responses');
const typeforms = require('./typeforms');

router.use('/responses', responses).use('/typeforms', typeforms);

module.exports = router;
