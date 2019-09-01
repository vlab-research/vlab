const mustache = require('mustache')
const util = require('util')
const _ = require('lodash')

const {parseLogJSON} = require('./utils')
const {translator, addCustomType}= require('@vlab-research/translate-typeform')

class FieldError extends Error {}

// TODO: move this to VALIDATORS somewhere
function formValidator(form){
  if (!form.fields.length) {
    throw new TypeError('This Typeform does not have any fields!')
  }
}

function getFromMetadata(ctx, key) {
  const {user, md} = ctx
  const meta = {...user, ...md }

  if (!meta[key]) {
    throw new TypeError(`Cannot create field text as the value ${key} does not exist in metadata ${util.inspect(meta)}`)
    }

  return meta[key]
}

function getDynamicValue(ctx, qa, v) {
  const [loc, key] = v.split(':')
  const val = loc === 'hidden' ?
    getFromMetadata(ctx, key) :
    getFieldValue(qa, key)

  if (!val) {
    throw new TypeError(`Trying to interpolate a non-existent value: ${v}`)
  }

  return val
}

function _zip(a,b) {
  // zips two arrays together, alternating, starting with a
  if (!a || !b) return a.concat(b)
  const len = a.length + b.length
  const arr =[]
  for (let i=0; i<len; i++) {
    i%2 ? arr.push(b.shift()) : arr.push(a.shift())
  }
  return arr
}

function _splitUrls(s) {
  const re = RegExp(/https?:\/\/[^\s]+/ig)
  const nonMatches = s.split(re).map(s => ['text', s])
  if (re.test(s)) {
    const matches = s.match(re).map(s => ['url', s])
    return _zip(nonMatches, matches).filter(a => !!a[1])
  }
  return nonMatches
}

function _interpolate(ctx, qa, s, encode) {
  const lookup = encode ?
        v => encodeURIComponent(getDynamicValue(ctx, qa, v)) :
        v => getDynamicValue(ctx, qa, v)

  return mustache.parse(s)
    .map(t => t[0] === 'name' ? lookup(t[1]) : t[1])
    .join('')
}

function interpolate(ctx, qa, s) {
  if (!s) return s

  return _splitUrls(s)
    .map(([type,val]) => {
      if (type === 'url') return _interpolate(ctx, qa, val, true)
      if (type === 'text') return _interpolate(ctx, qa, val, false)
    })
    .join('')
}

function interpolateField(ctx, qa, field) {
  const keys = ['title', 'properties.description']
  const out = {...field}
  keys.forEach(k => _.set(out, k, interpolate(ctx, qa, _.get(out, k))))
  return out
}

function translateField(ctx, qa, field) {
  return translator(addCustomType(interpolateField(ctx, qa, field)))
}

function getField({form}, field) {
  const question = form.fields.find(({ref}) => ref === field)

  if (!question) {
    throw new FieldError(`Could not find the requested field, ${field}, in our form!`)
  }

  return question
}

function _isLast(form, field) {
  const idx = form.fields.findIndex(({ref}) => ref === field)
  return idx === form.fields.length - 1
}

function _getNext(form, currentRef) {
  // TODO: work out this ending logic....
  // this should never be reached??
  if (_isLast(form, currentRef)) {
    return null
  }

  const idx = form.fields.findIndex(({ref}) => ref === currentRef)
  return form.fields[idx + 1]
}

function getNextField(ctx, qa, currentField) {
  const {form} = ctx

  const logic = ctx.form.logic && ctx.form.logic.find(({ref}) => ref === currentField)

  if (logic) {
    const nxt = jump(ctx, qa, logic)
    return getField(ctx, nxt)
  }

  return _getNext(form, currentField)
}


function jump(ctx, qa, logic) {

  const {ref, actions} = logic

  for (let {condition, details} of actions) {
    if (getCondition(ctx, qa, ref, condition)) return details.to.value
  }

  // Default to next field if none found
  return _getNext(ctx.form, ref)
}

function getFieldValue(qa, ref) {
  // last valid answer
  const match = qa.filter(([q,a]) => q === ref).pop()

  // return null if there are no matches,
  // or if there are no answers,
  const ans = match && match[1]
  return ans ? ans : null
}

const funs = {
  'and': (a,b) => a && b,
  'or': (a,b) => a || b,
  'greater_than': (a,b) => a > b,
  'lower_than': (a,b) => a < b,
  'greater_equal_than': (a,b) => a >= b,
  'lower_equal_than': (a,b) => a <= b,
  'is': (a,b) => a == b,
  'equal': (a,b) => a == b,
  'is_not': (a,b) => a != b,
  'not_equal': (a,b) => a != b,
  'always': () => true
}

function getCondition(ctx, qa, ref, {op, vars}){
  const fn = funs[op]
  if (!fn) {
    throw new TypeError(`Cannot find operation: ${op}\nquestion: ${ref}`)
  }
  return fn(...vars.map(v => getVar(ctx, qa, ref, v)))
}

function getChoiceValue({form}, ref, choice) {
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


function getVar(ctx, qa, ref, v) {
  if (v.op) {
    return getCondition(ctx, qa, ref, v)
  }

  const {type, value} = v

  if (type == 'constant') {
    return value
  }

  if (type == 'choice') {
    return getChoiceValue(ctx, ref, value)
  }

  if (type == 'field') {
    return getFieldValue(qa, value)
  }
}


module.exports = {
  getCondition,
  getFieldValue,
  jump,
  getField,
  getNextField,
  translateField,
  interpolateField,
  addCustomType,
  getFromMetadata,
  FieldError,
  _splitUrls
}
