const router = require('express').Router();
const responses = require('./responses');
const surveys = require('./surveys');

router.use('/responses', responses).use('/surveys', surveys);

module.exports = router;
