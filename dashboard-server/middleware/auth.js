const jwt = require('express-jwt');
const { JWT: clientConfig, SERVER_JWT: serverConfig } = require('../config');

// make middleware that tries auth0 client then if that fails
// tries auth0 server application...
function auth(req, res, next) {
  jwt(clientConfig)(req, res, (err, res) => {
    if (!err) return next();
    if (err && err.name === 'UnauthorizedError') {

      return jwt(serverConfig)(req, res, next);
    } else {
      return next(err);
    }
  });
}

module.exports = auth;
