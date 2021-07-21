// ***********************************************************
// This example support/index.js is processed and
// loaded automatically before your test files.
//
// This is a great place to put global configuration and
// behavior that modifies Cypress.
//
// You can change the location of this file or turn off
// automatically serving support files with the
// 'supportFile' configuration option.
//
// You can read more here:
// https://on.cypress.io/configuration
// ***********************************************************

// Import commands.js using ES2015 syntax:
import './commands';

Cypress.on('window:before:load', (window: any) => {
  window.handleFromCypress = async (
    request: import('miragejs').Request & { method: string }
  ) => {
    const response = await fetch(request.url, {
      method: request.method,
      headers: request.requestHeaders,
      body: request.requestBody,
    });

    const responseBody = await response.json();

    return {
      status: response.status,
      headers: response.headers,
      body: responseBody,
    };
  };
});
