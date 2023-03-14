import { defineConfig } from 'cypress'

export default defineConfig({
  video: false,
  env: {
    auth0_username: process.env.AUTH0_USERNAME,
    auth0_password: process.env.AUTH0_PASSWORD,
    auth0_domain: process.env.REACT_APP_AUTH0_DOMAIN,
    auth0_audience: process.env.REACT_APP_AUTH0_AUDIENCE,
    auth0_client_id: process.env.REACT_APP_AUTH0_CLIENT_ID,
    auth0_scope: 'openid email profile',
  },
  viewportHeight: 960,
  viewportWidth: 1536,
  e2e: {
    // We've imported your old cypress plugins here.
    // You may want to clean this up later by importing these.
    setupNodeEvents(on, config) {
      return require('./cypress/plugins/index.js')(on, config)
    },
    baseUrl: 'http://localhost:3000',
  },
})
