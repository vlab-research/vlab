const {
  translator,
  translateWelcomeScreen,
  translateThankYouScreen
} = require('typeform-to-facebook-messenger');

const translateForm = data => {
  const welcomeScreen = [];
  const thankYouScreen = [];

  if (data.welcome_screens) {
    const welcome = data.welcome_screens[0];
    let response = {
      response: translateWelcomeScreen(welcome),
      type: 'welcome_screen',
      ref: welcome.ref
    };
    welcomeScreen.push(response);
  }

  if (data.thankyou_screens) {
    const thankYou = data.thankyou_screens[0];
    let response = {
      response: translateThankYouScreen(thankYou),
      type: 'thankyou_screen',
      ref: thankYou.ref
    };
    thankYouScreen.push(response);
  }

  const translatedQuestions = data.fields.map(question => {
    return {
      response: translator(question, question.ref),
      // get validator...
      type: question.type,
      ref: question.ref
    }
  });

  const translatedForm = [
    ...welcomeScreen,
    ...translatedQuestions,
    ...thankYouScreen
  ];

  return translatedForm;
};

module.exports = translateForm;
