const translateShortText = data => {
  return { text: data.title }
}
//welcome_screen
const translateWelcomeScreen = data => {

  const response = translateShortText(data)
  response.quick_replies = [
    {
      content_type: 'text',
      title: data.properties.button_text,
      payload: data.properties.button_text,
    },
  ]
  return response
}

const translateLongText = translateShortText
const translateNumber = translateShortText
const translateDate = translateShortText

const translateStatement = data => {
  const response = translateShortText(data)
  response.metadata = { type: 'statement' }
  return response
}

const translateThankYouScreen = data => {
  const title = data.title.split('\n')[0]
  return translateStatement({ ...data, title })
}

const makeMultipleChoice = (text, choices, ref) => {

  // let's try multiple elements??
  const response = {text}
  response.quick_replies = choices.map(choice => {
    const [title, value] = Array.isArray(choice) ? choice : [choice.label, choice.label]
    return {
      content_type: 'text',
      title: title,
      payload: JSON.stringify({ value, ref }),
    }
  })

  return response
}

const _makeSimpleChoice = (text, choices, ref) => {
  const response = {}
  const buttons = choices.map(choice => {
    // use choice.id for multiple choice??
    const [title, value] = Array.isArray(choice) ? choice : [choice.label, choice.label]

    return {
      type: 'postback',
      title: title,
      payload: JSON.stringify({ value: value, ref: ref }),
    }
  })
  response.attachment = {
    type: 'template',
    payload: {
      template_type: 'button',
      text: text,
      buttons,
    },
  }
  return response
}

//multiple_choice
const translateMultipleChoice = (data, ref) => {
  return makeMultipleChoice(data.title, data.properties.choices, ref)
}

const translateDropDown = translateMultipleChoice

//yes_no to quick reply
const translateYesNo = (data, ref) => {
  return _makeSimpleChoice(data.title, [['Yes',true], ['No', false]], ref)
}

const translateLegal = (data, ref) => {
  return _makeSimpleChoice(data.title, [["I Accept", true], ["I don't Accept", false]], ref)
}

//email to quick reply (fb has qr button for sending email assoc with account)
const translateEmail = data => {
  const response = translateShortText(data)
  response.quick_replies = [
    {
      content_type: 'user_email',
      title: 'send email',
    },
  ]
  return response
}

//opinion scale to quick reply
const translateOpinionScale = data => {
  return translateRatings({...data, properties: { steps: 10 }})
}

const translateRatings = (data) => {
  const response = translateShortText(data)
  const steps = data.properties.steps

  response.quick_replies = new Array(steps)
    .fill('*')
    .map((e,i) => {
      return {
        content_type: 'text',
        title: `${i+1}`,
        payload: `${i+1}`,
      }
    })
  return response
}

//transform to carousel of generic templates
const translatePictureChoice = data => {
  const response = {}
  const elements = data.properties.choices.map(choice => {
    const buttons = [
      {
        type: 'postback',
        title: `select ${choice.label}`,
        payload: choice.label,
      },
    ]
    return {
      title: data.title,
      image_url: choice.attachment.href,
      buttons,
    }
  })
  response.attachment = {
    type: 'template',
    payload: {
      template_type: 'generic',
      elements,
    },
  }
  return response
}

const lookup = {
  'short_text': translateShortText,
  'multiple_choice': translateMultipleChoice,
  'email': translateEmail,
  'picture_choice': translatePictureChoice,
  'long_text': translateLongText,
  'welcome_screen': translateWelcomeScreen,
  'thankyou_screen': translateThankYouScreen,
  'legal': translateLegal,
  'yes_no': translateYesNo,
  'number': translateNumber,
  'statement': translateStatement,
  'opinion_scale': translateOpinionScale,
  'rating': translateRatings
}

function translator(question) {
  const fn = lookup[question.type]
  if (!fn) {
    throw new TypeError(`There is no translator for the question of type ${question.type}`)
  }
  const response = fn(question, question.ref)
  response.metadata = JSON.stringify({ ...response.metadata, ref: question.ref })
  return response
}

module.exports = {
  translator,
  translateWelcomeScreen,
  translateThankYouScreen,
  translateShortText,
  translateLongText,
  translateNumber,
  translateStatement,
  translateYesNo,
  translateMultipleChoice,
  translateDropDown,
  translateEmail,
  translateOpinionScale,
  translateRatings,
  translatePictureChoice,
  translateDate,
  translateLegal,
}
