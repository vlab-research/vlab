const r2 = require('r2')

async function getDashboardToken() {
  const body = { client_id: `${process.env.AUTH0_DASHBOARD_CLIENT_ID}`,
                 client_secret: `${process.env.AUTH0_DASHBOARD_SECRET}`,
                 audience: `${process.env.AUTH0_DASHBOARD_ID}`,
               grant_type: 'client_credentials'}

  const res = await r2.post(`${process.env.AUTH0_HOST}/oauth/token`, {json: body}).json
  const {access_token:token, token_type: tokenType } = res
  return {token, tokenType}
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
