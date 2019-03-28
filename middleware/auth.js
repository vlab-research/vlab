const jwt = require('express-jwt');
const { JWT: jwtConfig } = require('../config');

module.exports = jwt(jwtConfig);
