'use strict';

require('dotenv').config();
const joi = require('joi');
const jwks = require('jwks-rsa');

const envVarsSchema = joi
  .object({
    NODE_ENV: joi.string().allow(['development', 'production', 'test']),
    PORT: joi.number(),
    API_VERSION: joi.number(),
    AUTH0_HOST: joi.string().required(),
  })
  .unknown()
  .required();

const { error, value: envVars } = joi.validate(process.env, envVarsSchema);
if (error) {
  throw new Error(`Config validation error: ${error.message}`);
}

const config = {
  ENV: envVars.NODE_ENV,
  IS_DEVELOPMENT: envVars.NODE_ENV === 'development',
  SERVER: {
    PORT: envVars.PORT || 3000,
    API_VERSION: envVars.API_VERSION || '1',
  },
  JWT: {
    secret: jwks.koaJwtSecret({
      cache: true,
      rateLimit: true,
      jwksRequestsPerMinute: 10,
      jwksUri: `${envVars.AUTH0_HOST}/.well-known/jwks.json`,
    }),
    audience: 'http://localhost',
    issuer: envVars.AUTH0_HOST,
    algorithms: ['RS256'],
  },
};

module.exports = config;
