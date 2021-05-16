const router = require('express').Router();
const controller = require('./users.controller');

router.post('/', controller.createUser);

module.exports = router;
