// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add('login', (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add('drag', { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add('dismiss', { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite('visit', (originalFn, url, options) => { ... })
/* eslint-disable @typescript-eslint/no-namespace */

function loginViaAuth0Ui(username: string, password: string) {
  // App landing page redirects to Auth0.
  cy.visit('/')
cy.get('.loginbtn').click()
  // Login on Auth0.
  cy.origin(
    Cypress.env('auth0_domain'),
    { args: { username, password } },
    ({ username, password }) => {
      cy.get('#username').type(username)
      cy.get('#password').type(password, { log: false })
      cy.contains('button[value=default]', 'Continue').click()
    }
  )

  // Ensure Auth0 has redirected us back to the RWA.
  cy.url().should('equal', 'http://localhost:3000/')
}

Cypress.Commands.add('loginToAuth0', (username: string, password: string) => {
  const log = Cypress.log({
    displayName: 'AUTH0 LOGIN',
    message: [`🔐 Authenticating | ${username}`],
    // @ts-ignore
    autoEnd: false,
  })
  log.snapshot('before')
  cy.session(
    `auth0-${username}`,
    () => {
      loginViaAuth0Ui(username, password)
    },
    {}
  )
  log.snapshot('after')
  log.end()
})
