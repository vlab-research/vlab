'use strict';

const http = require('http');
const app = require('./server');

http.createServer(app).listen(3000);
