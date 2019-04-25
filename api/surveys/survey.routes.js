const router = require('express').Router();
const controller = require('./survey.controller');

router.post('/', controller.postOne);

module.exports = router;
