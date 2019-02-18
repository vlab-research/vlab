const {translator}= require('./translate-fields')

const message = 'Sorry, please try to answer the question again.'

function validateQR(field) {
  const q = translator(field)
  const titles = q.quick_replies.map(r => r.title)

  // Messenger will return us numbers in JSON,
  // so we need to cast them to strings, to compare with QR's
  return r => ({ message, valid: titles.indexOf(''+r) !== -1 })
}

function alwaysTrue(field) {
  return _ => ({ message, valid: true })
}

function validateStatement(field) {
  return _ => ({ message: 'No response is necessary.', valid: false })
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

function validateButton(field) {
  return r => {
    // TODO: validate potential text responses to the question.
    // return true if the text response is the same as a button
    // Right now, because it is a postback, it's auto-validated.
    // so for now we return false for any free-text entry.
    return { message: 'Sorry, please use the buttons provided to answer the question.',
             valid: false }
  }
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
  long_text: alwaysTrue
}

function validator(field) {
  const fn = lookup[field.type]
  if (!fn) {
    throw new TypeError(`There is no translator for the question of type ${field.type}`)
  }
  return fn(field)
}

module.exports = { validator }
