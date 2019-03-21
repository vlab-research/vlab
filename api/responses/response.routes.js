const Router = require('koa-router');
const controller = require('./response.controller');

const router = new Router();

router.get('/', controller.getAll);

module.exports = router;
