const zmq      = require('zeromq')
const frontend = zmq.socket('router')
const backend  = zmq.socket('dealer')

frontend.bindSync('tcp://*:4000');
backend.bindSync('tcp://*:4001');

frontend.on('message', function() {
  // Note that separate message parts come as function arguments.
  var args = Array.apply(null, arguments);
  // Pass array of strings/buffers to send multipart messages.
  backend.send(args);
});

backend.on('message', function() {
  var args = Array.apply(null, arguments);
  frontend.send(args);
});
