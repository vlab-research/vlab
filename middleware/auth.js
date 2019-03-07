const jwt = require('koa-jwt');
const { JWT: jwtConfig } = require('../config');

module.exports = jwt(jwtConfig);
