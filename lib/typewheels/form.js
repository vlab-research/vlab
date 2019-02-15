const {parseLogJSON} = require('./utils')

// TODO: move this to VALIDATORS somewhere
function formValidator(form){
  if (!form.fields.length) {
    throw new TypeError('This Typeform does not have any fields!')
  }
}

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
  const l = parseLogJSON(log)

  const logic = form.logic && form.logic.find(({ref}) => ref === currentField)

  if (logic) {
    const nxt = jump(form, l, logic)
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
  const ref = logic.ref

  for (let {condition, details} of logic.actions) {
    if (getCondition(form, log, ref, condition)) return details.to.value
  }

  // TODO: check that Typeform always gives an "always" action,
  // else return a default here (next question...)
  throw new Error('No action found for the given logic jump')
}


function getFieldValue(form, log, ref) {

  // TODO: logstate not needed! simplify!
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

function getCondition(form, log, ref, {op, vars}){
   return funs[op](...vars.map(v => getVar(form, log, ref, v)))
}

function getChoiceValue(form, ref, choice) {
  const val = form.fields
        .find(f => f.ref === ref)
        .properties.choices
        .find(c => c.ref === choice)
        .label

  if (!val) {
    throw new TypeError(`Could not find value for choice: ${choice} in question ${ref}`)
  }

  return val
}


function getVar(form, log, ref, v) {
  if (v.op) {
    return getCondition(form, log, ref, v)
  }

  const {type, value} = v

  if (type == 'constant') {
    return value
  }

  if (type == 'choice') {
    return getChoiceValue(form, ref, value)
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
  jump,
  getField,
  getNextField,
}
