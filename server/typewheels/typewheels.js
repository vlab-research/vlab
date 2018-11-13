
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
