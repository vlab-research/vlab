const {translator}= require('./translate-fields')

// allow for custom error messages from metadata!

const defaultMessages = {
  'label.error.mustEnter': 'Sorry, please try to answer the question again.',
  'label.error.mustSelect': 'Sorry, please use the buttons provided to answer the question.'
}

function _validateMC(titles, messages) {

  // Messenger will return us numbers in JSON,
  // but typeform mostly uses strings, except for booleans.
  // So we cast everything to strings, to compare with QR's

  return r => ({ message: messages['label.error.mustSelect'],
                 valid: titles.map(t => ''+t ).indexOf(''+r) !== -1 })
}

function validateQR(field, messages) {
  const q = translator(field)
  const titles = q.quick_replies.map(r => r.title)

  return _validateMC(titles, messages)
}

function alwaysTrue(field, messages) {

  // should not need a message, it's always valid!
  return _ => ({ message: 'Error', valid: true })
}

function validateStatement(field, messages) {

  // this could be made more generic, but enough for now.
  const {responseMessage} = field.md ? field.md : {}
  return _ => ({ message: responseMessage || 'No response is necessary.', valid: false })
}

function _isNumber(num) {
  if (typeof num === 'string') {
    num = num.trim()
    return !!num && num*0 === 0
  }
  // This assumes that if it's not a string, it's a number.
  return true
}

function validateNumber(field) {
  return r => ({ message: 'Sorry, please enter a valid number.',
                 valid: _isNumber(r) })
}

function validateButton(field, messages) {
  const q = translator(field)

  const titles = q.attachment.payload.buttons
        .map(r => JSON.parse(r.payload).value)

  return _validateMC(titles, messages)
}


const lookup = {
  number: validateNumber,
  statement: validateStatement,
  thankyou_screen: validateStatement,
  multiple_choice: validateQR,
  rating: validateQR,
  opinion_scale: validateQR,
  legal: validateButton,
  yes_no: validateButton,
  short_text: alwaysTrue,
  long_text: alwaysTrue,
  share: validateStatement,
  webview: validateStatement
}

// should just get messages directly?
function validator(field, messages = {}) {
  messages = {...defaultMessages, ...messages}

  const fn = lookup[field.type]
  if (!fn) {
    throw new TypeError(`There is no translator for the question of type ${field.type}`)
  }
  return fn(field, messages)
}

module.exports = { validator }
