const Router = require('koa-router');
const user = require('./users/user.routes');

const { API_VERSION } = require('../config').SERVER;

const router = new Router({
  prefix: `/api/v${API_VERSION}`,
});

router.use('/users', user.routes());

module.exports = router;
