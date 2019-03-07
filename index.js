'use strict';

const http = require('http');
const app = require('./server');

const { PORT } = require('./config').SERVER;

http.createServer(app.callback()).listen(PORT);
