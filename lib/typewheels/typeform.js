const r2 = require('r2')

function translateForm(form, messages) {
  const f = {...form}
  f.fields = [...f.fields, ...f.thankyou_screens.map(s => ({...s, type: 'thankyou_screen'}))]
  f.custom_messages = messages

  return f
}

async function getMessages(form, headers) {
  const res = await r2(`https://api.typeform.com/forms/${form}/messages`, {headers}).response
  return await res.json()
}

async function getForm(form) {
  if (!form) {
    throw new TypeError(`Trying to get a form without a value!`)
  }
  const headers = {Authorization: `Bearer ${process.env.TYPEFORM_KEY}`}
  const res = await r2(`https://api.typeform.com/forms/${form}`, {headers}).response
  const f = await res.json()
  if (f.code) {
    throw new Error(JSON.stringify(f))
  }
  const messages = await getMessages(form, headers)
  return translateForm(f, messages)
}

module.exports = { getForm }
