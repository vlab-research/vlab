const router = require('express').Router();
const controller = require('./facebook.controller');

router.post('/exchange-token', controller.exchangeToken);

module.exports = router;
