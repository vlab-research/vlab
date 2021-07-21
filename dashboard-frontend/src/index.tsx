import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
import { makeServer } from './server';
import { Server, Request, Response } from 'miragejs';

if (window.Cypress) {
  const handleRequest = async (_: unknown, request: Request) => {
    const { status, headers, body } = await window.handleFromCypress(request);
    return new Response(status, headers, body);
  };

  // mirage cypress server
  const cyServer = new Server({
    routes() {
      this.get('/*', handleRequest);
      this.put('/*', handleRequest);
      this.patch('/*', handleRequest);
      this.post('/*', handleRequest);
      this.delete('/*', handleRequest);
      this.options('/*', handleRequest);
    },
  });

  cyServer.logging = false;
} else {
  // mirage dev server
  makeServer();
}

ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById('root')
);
