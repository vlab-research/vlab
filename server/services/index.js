const r2 = require('r2')

const verifyToken = ctx => {
  if (ctx.query['hub.verify_token'] === process.env.VERIFY_TOKEN) {
    ctx.body = ctx.query['hub.challenge']
    ctx.status = 200
  } else {
    ctx.body = 'invalid verify token'
    ctx.status = 401
  }
};

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

// Gets user by assuming page ID to be constant.
function getUser(event) {
  const PAGE_ID = process.env.FB_PAGE_ID

  if (event.sender.id == PAGE_ID) {
    return event.recipient.id
  }
  else if (event.recipient.id == PAGE_ID){
    return event.sender.id
  }
  else {
    throw new Error('Non Existent User!')
  }
}

module.exports = { verifyToken, getForm, getUser };
