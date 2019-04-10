require('chai').should();
const sender = require('../services/sender.js');
const app = require('../services/receiver.js');
const mocks = require('./mocks');

describe('Test Bot flow Survey Integration Testing', () => {
  
  let server;
  let testFlow = [];
  let state = 0;
  let bindedDone;
  
  before(() => {
    server = app.listen(process.env.PORT || 88);
    console.log('Test starting!');
  });

  after(() => {
    server.close();
    console.log('Server closed!');
  });
  
  it('Test chat flow with logic jump "Yes"',  (done) => {
    bindedDone = done.bind(this)
    testFlow = [
      [mocks.acceptMessage, [mocks.acceptEcho, mocks.acceptPostback]],
      [mocks.questionMessage, [mocks.questionEcho, mocks.questionPostbackYes]],
      [mocks.funMessage, [mocks.funEcho, mocks.funPostback]],
      [mocks.thanksMessage, [mocks.thanksEcho]],
      [mocks.endMessage, [mocks.endEcho]],
    ]; 

    sender(mocks.referral);

  }).timeout(10000);

  it('Test chat flow with logic jump "No"',  (done) => {
    bindedDone = done.bind(this)
    testFlow = [
      [mocks.acceptMessage, [mocks.acceptEcho, mocks.acceptPostback]],
      [mocks.questionMessage, [mocks.questionEcho, mocks.questionPostbackNo]],
      [mocks.boringMessage, [mocks.boringEcho]],
      [mocks.endMessage, [mocks.endEcho]],
    ];

    sender(mocks.referral);

  }).timeout(10000);

  app.on('message', async ({message}) => {
    const [get, gives] = testFlow[state]
    message.should.eql(get);
    for (let giv of gives) {
      await sender(giv);
    }
    state++
    if (state == testFlow.length) {
      state = 0;
      bindedDone();
    }
  })

});
