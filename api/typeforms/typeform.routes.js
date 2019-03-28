const router = require('express').Router();
const controller = require('./typeform.controller');

router.post('/', controller.postOne);

module.exports = router;
