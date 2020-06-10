const r2 = require('r2')
const jwt = require('jsonwebtoken')


// TODO: move off auth0, create our own endpoint
// or just put a token in the env vars and call
// it a day.
async function getDashboardToken() {
  const secret = process.env.AUTH0_DASHBOARD_SECRET
  const opts = { algorithm: 'HS256'}

  return new Promise((resolve, reject) => {
    jwt.sign({}, secret, opts, (err, token) => {
      if (err) return reject(err);

      resolve({token, tokenType: 'Bearer'})
    })
  })
}


function translateForm(form, messages) {
  const f = {...form}
  f.fields = [...f.fields, ...f.thankyou_screens.map(s => ({...s, type: 'thankyou_screen'}))]
  f.custom_messages = messages
  return f
}



async function getForm(pageid, shortcode, timestamp) {
  if (!pageid || !shortcode || !timestamp) {
    throw new TypeError(`Trying to get a form without a pageid or shortcode or timestamp! ${pageid}, ${shortcode}, ${timestamp}`)
  }

  const {token, tokenType} = await getDashboardToken()

  const headers = {Authorization: `${tokenType} ${token}`}
  const url = `${process.env.DASHBOARD_API}/surveys?pageid=${pageid}&shortcode=${shortcode}&timestamp=${timestamp}`

  const res = await r2(url, { headers }).response

  try {
    const f = await res.json()
    const {id:surveyId, form, messages} = f
    return [translateForm(JSON.parse(form), messages), surveyId]
  }
  catch (e) {
    console.error('ERROR PARSING REPLY FROM FORM SERVER: ', res)
    throw e
  }

}

module.exports = { getForm }
