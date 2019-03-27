const router = require('express').Router();
const controller = require('./response.controller');

router.get('/', controller.getAll);

module.exports = router;
