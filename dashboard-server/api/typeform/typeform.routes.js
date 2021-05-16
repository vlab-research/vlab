const router = require('express').Router();
const controller = require('./typeform.controller');

router.get('/auth/:code', controller.authorize);
router.get('/form', controller.getForm);

module.exports = router;
