'use strict';

const joi = require('joi');
const jwks = require('jwks-rsa');

const envVarsSchema = joi
  .object({
    NODE_ENV: joi.string().allow(['development', 'production', 'test']),
    API_VERSION: joi.number(),
    AUTH0_HOST: joi.string(),
    DB_USER: joi.string(),
    DB_HOST: joi.string(),
    DB_PASSWORD: joi
      .string()
      .optional()
      .empty(''),
    DB_DATABASE: joi.string(),
    DB_PORT: joi.number(),
    FORMCENTRAL_URL: joi.string(),
    AUTH0_CLIENT_ID: joi.string(),
    AUTH0_DASHBOARD_SECRET: joi.string()
  })
  .unknown()
  .required();

const { error, value: envVars } = joi.validate(process.env, envVarsSchema);
if (error) {
  throw new Error(`Config validation error: ${error.message}`);
}

const isTest = () => envVars.NODE_ENV === 'test';

const config = {
  ENV: envVars.NODE_ENV,
  IS_DEVELOPMENT: envVars.NODE_ENV === 'development',
  IS_TEST: isTest(),
  FORMCENTRAL: {
    url: envVars.FORMCENTRAL_URL,
  },
  SERVER: {
    API_VERSION: envVars.API_VERSION || '1',
  },
  TYPEFORM: {
    typeformUrl: envVars.TYPEFORM_URL || '',
    secret: envVars.TYPEFORM_CLIENT_SECRET || '',
    clientId: envVars.TYPEFORM_CLIENT_ID || '',
    redirectUri: envVars.TYPEFORM_REDIRECT_URL || '',
  },
  JWT: {
    secret: jwks.expressJwtSecret({
      cache: true,
      rateLimit: true,
      jwksRequestsPerMinute: 10,
      jwksUri: `${envVars.AUTH0_HOST}/.well-known/jwks.json`,
    }),
    audience: envVars.AUTH0_CLIENT_ID,
    issuer: `${envVars.AUTH0_HOST}/`,
    algorithms: ['RS256'],
  },
  SERVER_JWT: {
    secret: envVars.AUTH0_DASHBOARD_SECRET
  },
  DATABASE_CONFIG: {
    user: isTest() ? 'root' : envVars.DB_USER || 'postgres',
    host: isTest() ? 'localhost' : envVars.DB_HOST || 'localhost',
    database: isTest() ? 'chatroach' : envVars.DB_DATABASE || 'postgres',
    password: isTest() ? undefined : envVars.DB_PASSWORD || undefined,
    port: isTest() ? 5433 : envVars.DB_PORT || 5432,
  },
};

module.exports = config;
