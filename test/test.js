require('chai').should();
const mocks = require('./mocks');
const sender = require('../services/sender.js');
const app = require('../services/receiver.js');

describe('Test Bot flow Survey1', () => {
  
  const server = app.listen(process.env.PORT || 88);

  before(() => {
    console.log('Test starting!');
  });

  after(() => {
    server.close();
    console.log('Server closed!');
  });
  
  it('Start the conversation and should receive Accept Message',  (done) => {
    let state = 1;
    sender(mocks.referral);
    app.on('message', async ({message}) => {
      switch (state) {
        case 1:
          message.should.eql(mocks.acceptMessage)
          await sender(mocks.acceptEcho);
          await sender(mocks.acceptPostback);
          break;
        case 2:
          message.should.eql(mocks.questionMessage)
          await sender(mocks.questionEcho);
          await sender(mocks.questionPostback);
          break;
        case 3:
          message.should.eql(mocks.thanksMessage)
          sender(mocks.thanksEcho);
          break;
        case 4:
          message.should.eql(mocks.endMessage)
          sender(mocks.endEcho);
          done();
          break;
        default:
          break;
      }
        state++;
    })
  }).timeout(10000);

});
