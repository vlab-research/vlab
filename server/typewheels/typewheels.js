
// turn logic jumps into referring to ONE response to a sent.
// responses should be ignored if they don't validate with the type of question.

// basically, everything needs to fit into a series of Q:A pairs
// The answer refers to the last Q
// If answer doesn't validate, repeat Q!
// If answer does validate, run through LOGIC JUMPS associated with that Q, to determine next Q
// Send next Q

// one to get vars (in the case of nested op, it should recurse via op)

// one to deal with op

// These need to be recursive in the case of or...

// vars

module.exports = {
  getField,
  getVar,
  getCondition,
  getState,
  getLogState,
  getWatermark
}

// orderedMap???
const util = require('util')


// was delivered --> check to see if question was delivered!
// if delivered --> check to see if read
// mark read/delivered somehow...
// use watermark??

const withAnswers = f => f.filter(([k,v]) => !!v.length)

// defaults to returning 0!!!!!
function getWatermark(type, log) {
  return log
    .filter(i => i[type])
    .map(i => i[type].watermark)
    .reduce((a,b) => a > b ? a : b, 0)
}

function getReferral(log) {
  const ref = log.filter(i => i.referral).map(i => i.referral.ref).pop()
  return ref.split('.')[0] // TODO: come up with format to get form!
}

function addAnswerToQuestion(state, ref, event) {
  for (let [k, v] of state) {
    try {
      const md = JSON.parse(k.message.metadata)
      if (md.ref == ref) {
        v.push(event)
      }
    }
    catch(e) {
      console.error(e)
    }
  }
  return state
}

function addPostbackToState(state, event) {
  const { value, ref } = JSON.parse(event.postback.payload)
  return addAnswerToQuestion(state, ref, event)
}

function getLastSeenQuestion (log) {
  const readWatermark = getWatermark('read', log)
  const deliveryWatermark = getWatermark('delivery', log)

  return log
    .filter(i => i.message && i.message.is_echo)
    .filter(i => i.timestamp < readWatermark )
    .map(i => JSON.parse(i.message.metadata))
    .map(i => i.ref)
    .pop()

}

// should be recursive -- should first do for one, then continue...
// purpose should be to REORDER! Based on how user experiences it.
// if answer comes in, and current watermarks are such that question


// put questions aside
// keep track of watermarks
// once question delivered/read, allow it
// { question, responses, watermark, restoflist }


function getLogState(log) {
  const readWatermark = getWatermark('read', log)
  const deliveryWatermark = getWatermark('delivery', log)
  const form = getReferral(log)

  const history = log
        .reduce((state, nxt, i) => {

          // only add questions and postbacks!
          if (!(nxt.message || nxt.postback)) {
            return state
          }

          const [last] = state.slice(-1)

          // New question, push to state
          if (nxt.message && nxt.message.is_echo) {
            return [...state, [nxt, []]]
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

  return { readWatermark, deliveryWatermark, form, history }
}

function getState(logstate) {

  // get last seen question??
  const [question, responses] = logstate.history.pop() || []

  // impliment this for reduce above!
  // if they send a message after I've responded, but before they've read it, count it as the next message...

  const isRead = !!question && logstate.readWatermark > question.timestamp
  const isDelivered = !!question && logstate.deliveryWatermark > question.timestamp
  const isValid = !!responses // put in validation!

  // helpOutstanding!!??

  return {
    question,
    responses,
    isValid
  }
}

function stateMachine(form, state) {
  // given state and form
  // this function should transition...

  // if no question, go to first question

  // if helpOutstanding, go to help >> pop from responses for past state
  // if no helpOutstanding, remove help from state if exists and continue

  // if question and no responses, do nothing

}

// logic 0...

// 378caa71-fc4f-4041-8315-02b6f33616b9
// 3edb7fcc-748c-461c-bacd-593c043c5518



function getResponse(form, log) {

  // get state
  const state = getState(log)

  // run through state machine with form

  // return question associated with next state!
}


function getField(form, ref) {
  // We should look in our own data format for the value of this field...
  // This would be the last answer that came after this field...
  // returns undefined in case of no match...
  // takes history
  const matches = form.fields.filter(f => f.ref == ref)
  return matches[0]
}

const funs = {
  'or': (a,b) => a || b,
  'greater_than': (a,b) => a > b,
  'lower_than': (a,b) => a < b,
  'is': (a,b) => a === b,
  'always': () => true
}

function getCondition(form, {op, vars}){
  return funs[op](...vars.map(v => getVar(form, v)))
}


function getVar(form, v) {
  if (v.op) {
    return getCondition(form, v)
  }

  const {type, value} = v

  if (type == 'constant') {
    return value
  }

  if (type == 'field') {
    return getField(form, value)
  }
}
