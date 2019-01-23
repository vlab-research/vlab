const {recursiveJSONParser, parseLogJSON, getForm, splitLogsByForm} = require('./utils')
const {validator} = require('./validator')
const {translator}= require('typeform-to-facebook-messenger')

// defaults to returning 0!!!!!
function getWatermark(type, log) {
  return log
    .filter(i => i[type])
    .map(i => i[type].watermark)
    .reduce((a,b) => a > b ? a : b, 0)
}


function addAnswerToQuestion(state, ref, event) {
  for (let [k, v] of state) {
    if (k == ref) {
      v.push(event)
    }
  }
  return state
}

function addPostbackToState(state, event) {
  const { value, ref } = event.postback.payload
  return addAnswerToQuestion(state, ref, event)
}

function getLastSeenQuestion (log) {
  const readWatermark = getWatermark('read', log)
  const deliveryWatermark = getWatermark('delivery', log)

  return log
    .filter(i => i.message && i.message.is_echo)
    .filter(i => i.timestamp <= readWatermark )
    .map(i => i.message.metadata.ref)
    .pop()

}

const getQuestion = event => event.message.metadata.ref

function getLogState(log) {
  return parseLogJSON(log)
    .reduce((state, nxt, i) => {

      // only add questions and postbacks!
      if (!(nxt.message || nxt.postback)) {
        return state
      }

      const [last] = state.slice(-1)

      // New question, push to state
      if (nxt.message && nxt.message.is_echo) {

        // If there is no metadata, it's not ours.
        // So we should ignore it.
        if (!nxt.message.metadata) return state

        return [...state, [getQuestion(nxt), []]]
      }

      // Postbacks need special treatment!
      else if (nxt.postback) {
        return addPostbackToState(state, nxt)
      }

      // Add the response to the last question
      const ref = getLastSeenQuestion(log.slice(0, i+1))
      if (ref) {
        return addAnswerToQuestion(state, ref, nxt)
      }

      // If there is no last question, state isnt updated
      return state
    }, [])
}

// move this to VALIDATORS somewhere
function formValidator(form){
  if (!form.fields.length) {
    throw new TypeError('This Typeform does not have any fields!')
  }
}

function repeatResponse(question, text='Sorry, please answer the question again.') {
  return {
    text,
    metadata: JSON.stringify({ repeat: true, ref: question })
  }
}

class Machine {
  exec (state, ...rest) {
    const fns = {
      'START': this.start,
      'QA': this.qA,
      'QOUT': this.qOut,
      'REPEAT': this.repeat
    }
    return fns[state.state](state, ...rest)
  }

  start (state, form) {
    const field = form.fields[0]
    return translator(field)
  }

  qA ({ question, response, prevalid }, form, log) {
    // if validation fails...
    const {valid, message} = validate(question, response, form, prevalid)

    if (!valid) {
      return repeatResponse(question, message)
    }

    const field = getNextField(form, log, question)

    // TODO: if last question??? Now we return null??
    return field ? translator(field) : null
  }

  // repeat, question
  // send "repeat message" + question
  repeat({ question }, form, log) {
    const field = getField(form, question)
    return translator(field)
  }

  qOut({ question, time}, form, log){
    // do nothing ?
    // send reminder
  }
}

function validate(question, response, form, prevalid) {
  if (prevalid !== undefined) return { valid: prevalid }


  const field = getField(form, question)
  return validator(field)(response)
}

function getField(form, field) {
  const question = form.fields.find(({ref}) => ref === field)

  if (!question) {
    throw new TypeError(`Could not find the requested field, ${field}, in our form!`)
  }

  return question
}

function isLast(form, field) {
  const idx = form.fields.findIndex(({ref}) => ref === field)
  return idx === form.fields.length - 1
}


function getNextField(form, log, currentField) {
  const logic = form.logic && form.logic.find(({ref}) => ref === currentField)

  if (logic) {
    const nxt = jump(form, log, logic)
    return getField(form, nxt)
  }

  // TODO: work out this ending logic....
  // this should never be reached??
  if (isLast(form, currentField)) {
    return null
  }

  const idx = form.fields.findIndex(({ref}) => ref === currentField)
  return form.fields[idx + 1]
}

const util = require('util')

function jump(form, log, logic) {
  for (let {condition, details} of logic.actions) {
    if (getCondition(form, log, condition)) return details.to.value
  }

  // TODO: check that Typeform always gives an "always" action,
  // else return a default here (next question...)
  throw new Error('No action found for the given logic jump')
}


function getFieldValue(form, log, ref) {

  const logState = getLogState(log)
  const match = logState.find(([q,a]) => q === ref)

  // return null if there are no matches,
  // or if there are no answers,
  const ans = match && match[1].pop()
  if (!ans) return null

  if (ans.message) return ans.message.text
  if (ans.postback) return ans.postback.payload.value
}

const funs = {
  'or': (a,b) => a || b,
  'greater_than': (a,b) => a > b,
  'lower_than': (a,b) => a < b,
  'is': (a,b) => a == b, // double equals to cast string into numbers!
  'always': () => true
}

function getCondition(form, log, {op, vars}){
   return funs[op](...vars.map(v => getVar(form, log, v)))
}


function getVar(form, log, v) {
  if (v.op) {
    return getCondition(form, log, v)
  }

  const {type, value} = v

  if (type == 'constant') {
    return value
  }

  if (type == 'field') {
    return getFieldValue(form, log, value)
  }
}

module.exports = {
  getWatermark,
  getCondition,
  getLogState,
  getFieldValue,
  splitLogsByForm,
  jump,
  getNextField,
  Machine
}
