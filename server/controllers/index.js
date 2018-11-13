const { handleMessage } = require('./messageHandler');

const startSurvey = async ctx => {
  try {
    const body = ctx.request.body;
    console.log(body)

    if (body.object === 'page') {
      body.entry.forEach(entry => {
        let event;



        event = entry.messaging[0];

        console.log('EVENT: ', event)

        if ((event.message && !event.message.is_echo) ||
            (event.postback && event.postback.payload)) {

          handleMessage(event);
        }
        ctx.status = 200;
      });
    } else {
      ctx.status = 404;
    }
  } catch (error) {
    console.error('[ERR] startSurvey: ', error);
  }
};

module.exports = { startSurvey };
