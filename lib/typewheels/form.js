const mustache = require('mustache')
const util = require('util')
const _ = require('lodash')
const {translator, addCustomType}= require('@vlab-research/translate-typeform')
const yaml = require('js-yaml')

class FieldError extends Error {}

// TODO: move this to VALIDATORS somewhere
// function formValidator(form){
//   if (!form.fields.length) {
//     throw new TypeError('This Typeform does not have any fields!')
//   }
// }



function getSeed(md, key) {
  const [__, match] = /seed_(\d+)/.exec(key)
  const seeds = +match
  return md.seed % seeds + 1
}

// METADATA consists of:
// 1. Anything on the user object (id, name, first_name, last_name)
// 2. Anything sent in the original url "ref" query param (i.e. form, via ?ref=form.foo)
// 3. A random seed, given by 'seed_2' or 'seed_7' or 'seed_N' for any number needed
function getFromMetadata(ctx, key) {
  const {user, md} = ctx

  if (/seed_/.test(key)) return getSeed(md, key)

  const meta = {...user, ...md }

  if (meta[key] === undefined) {
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

function getField({form, user}, ref, index=false) {
  if (!form.fields.length) {
    throw new FieldError(`This form has no fields: ${form.id}`)
  }

  const idx = form.fields.map(({ref}) => ref).indexOf(ref)
  const field = form.fields[idx]

  if (!field) {
    throw new FieldError(`Could not find the requested field, ${ref},
                          in our form: ${form.id}, for user id: ${user.id}!`)
  }

  return index ? [idx, field] : field
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

  const logic = form.logic && form.logic.find(({ref}) => ref === currentField)

  if (logic) {
    const nxt = jump(ctx, qa, logic)
    const field = getField(ctx, nxt)
    return field
  }

  return _getNext(form, currentField)
}


function jump(ctx, qa, logic) {
  // TODO: Handle case where logic fails and
  // there is no default -- proper error and
  // maybe work out a new state... "blocked?"

  const {ref, actions} = logic

  for (let {condition, details} of actions) {
    if (getCondition(ctx, qa, ref, condition)) {
      return details.to.value
    }
  }

  // Default to next field if none found
  return _getNext(ctx.form, ref).ref
}

function getFieldValue(qa, ref) {
  // last valid answer
  const match = qa.filter(([q,__]) => q === ref).pop()

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
  'is': (a,b) => a === b,
  'equal': (a,b) => a === b,
  'is_not': (a,b) => a !== b,
  'not_equal': (a,b) => a !== b
}


function getCondition(ctx, qa, ref, {op, vars}){
  if (op === 'always') return true

  const f = funs[op]

  if (!f) {
    throw new TypeError(`Cannot find operation: ${op}\nquestion: ${ref}`)
  }

  // wrap in yaml safe-load to perform type-casting
  // from form data (strings) to js native types
  // i.e. boolean, null, etc.
  const fn = (a, b) => f(yaml.safeLoad(a), yaml.safeLoad(b))

  // getChoiceValue needs to ref from the "field" type,
  // which it is always paired with....

  // vars should be length 2 unless and/or in which case
  // can be length unlimited so we reduce through logic
  return vars.map((v)=> getVar(ctx, qa, ref, v, vars)).reduce(fn)
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


function getVar(ctx, qa, ref, v, vars) {
  if (v.op) {
    return getCondition(ctx, qa, ref, v)
  }

  const {type, value} = v

  if (type == 'constant') {
    return value
  }

  if (type == 'choice') {
    const field = vars.find(v => v.type === 'field').value
    return getChoiceValue(ctx, field, value)
  }

  if (type == 'field') {
    return getFieldValue(qa, value)
  }

  if (type == 'hidden') {
    return getFromMetadata(ctx, value)
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
