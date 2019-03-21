const Router = require('koa-router');
const responses = require('./responses/response.routes');

const { API_VERSION } = require('../config').SERVER;

const router = new Router({
  prefix: `/api/v${API_VERSION}`,
});

router.use('/responses', responses.routes());

module.exports = router;
