const { Router } = require('express');
const responses = require('./responses/response.routes');

const { API_VERSION } = require('../config').SERVER;

const router = Router({
  prefix: `/api/v${API_VERSION}`,
});

router.use('/responses', responses);

module.exports = router;
