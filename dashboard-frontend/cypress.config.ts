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
    REACT_APP_SERVER_URL: "http://localhost:8080"
  },
  viewportHeight: 960,
  viewportWidth: 1536,
  defaultCommandTimeout: 10000,
  e2e: {
    baseUrl: 'http://localhost:3000',
  },
})
