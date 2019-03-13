require('chai').should();
const mocks = require('./mocks');
const sender = require('../services/sender.js');
const app = require('../services/receiver.js');

describe('Should send&receive ', () => {
  
  const server = app.listen(process.env.PORT || 88);

  before(() => {
    console.log('Test starting!');
  });

  after(() => {
    server.close();
    console.log('Server closed!');
  });
  
  it('Sender should send a POST request to Botserver',  (done) => {
    sender(mocks.referral);
    app.on('message', (message) => {
      console.log('message', message);
      done()
    })
  }).timeout(5000);
});
