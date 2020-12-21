const router = require('express').Router();
const controller = require('./credentials.controller');

router.post('/', controller.createCredential);
router.get('/', controller.getCredentials);

module.exports = router;
