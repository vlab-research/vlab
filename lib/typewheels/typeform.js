const r2 = require('r2')

function translateForm(form) {
  const f = {...form}
  f.fields = [...f.fields, ...f.thankyou_screens.map(s => ({...s, type: 'thankyou_screen'}))]
  return f
}

async function getForm(form) {
  const headers = {Authorization: `Bearer ${process.env.TYPEFORM_KEY}`}
  const res = await r2(`https://api.typeform.com/forms/${form}`, {headers}).response
  const f = await res.json()
  return translateForm(f)
}

module.exports = { getForm }
