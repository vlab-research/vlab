const typeformForm = require('./typeform-form')
const {
  translateWelcomeScreen,
  translateShortText,
  translateMultipleChoice,
} = require('../../app/functions')

const fields = new Map()

typeformForm.fields.forEach(question => {  

  let response
  function setQuestion (response) {
    fields.set(question['ref'], response)
  }

  switch (question.type) {
  case 'welcome_screen':
    response = translateWelcomeScreen(question)
    setQuestion(response)
    return
  case 'short_text':
    response = translateShortText(question)
    setQuestion(response)
    return
  case 'multiple_choice':
    response = translateMultipleChoice(question)
    setQuestion(response)
    return
  default:
    setQuestion({text: question.title})
    return
  }
})

//account for more than one welcome screen
const facebookForm = {
  id: 'icsypX',
  title: 'Mars Mission',
  welcome_screens: [
    {
      ref: '111e9906-af75-498f-846c-2a1752245696',
      text: 'Come aboard the Dragon!',
      quick_replies: [
        {
          content_type: 'text',
          title: 'Begin Mission',
          payload: 'Begin Mission',
        },
      ],
    },
  ],
  thankyou_screens: [
    {
      ref: '76fce4b1-df4d-4fbd-977e-8b5532c7ebf2',
      text: 'Thank you for joining us aboard the Dragon!',
      quick_replies: [
        {
          content_type: 'text',
          title: 'End survey',
          payload: 'End survey',
        },
      ],
    },
  ],
  fields: fields,
}

for (let [key, value] of facebookForm.fields) {
  console.log('log', key, ' ', value)
}