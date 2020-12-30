const router = require('express').Router();
const controller = require('./facebook.controller');

router.post('/exchange-token', controller.exchangeToken);
router.post('/webhooks', controller.addWebhooks);
router.post('/get-started', controller.addGetStarted);

module.exports = router;
