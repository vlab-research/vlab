const {translator}= require('typeform-to-facebook-messenger')

function validateQR(field) {
  const q = translator(field)
  const titles = q.quick_replies.map(r => r.title)

  return r => ({ valid: titles.indexOf(''+r) !== -1 })
}

function alwaysTrue(field) {
  return _ => ({ valid: true })
}

function validateStatement(field) {
  return _ => ({ valid: false, message: 'No response is necessary. Please read my message:' })
}

function _isNumber(num) {
  if (typeof num === 'string') {
    num = num.trim()
    return { valid: !!num && num*0 === 0 }
  }
  return {valid: true} // if it's not a string, it's a number???
}

function validateNumber(field) {
  return {valid: _isNumber}
}

function validateButton(field) {
  return r => {
    // TODO: validate potential text responses to the question.
    // return true if the text response is the same as a button
    return { valid: false }
  }
}


const lookup = {
  number: validateNumber,
  statement: validateStatement,
  multiple_choice: validateQR,
  rating: validateQR,
  opinion_scale: validateQR,
  legal: validateButton,
  short_text: alwaysTrue,
  long_text: alwaysTrue
  // add opinion scale and rating
}

function validator(field) {
  const fn = lookup[field.type]
  if (!fn) {
    throw new TypeError(`There is no translator for the question of type ${field.type}`)
  }
  return fn(field)
}

module.exports = { validator }
