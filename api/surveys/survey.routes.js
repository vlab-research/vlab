const router = require('express').Router();
const controller = require('./survey.controller');

router.post('/', controller.postOne);
router.get('/', controller.getBy, controller.getAll);


module.exports = router;
