'use strict';
const request = require('request');
const r2 = require('r2');

const { TYPEFORM: { typeformUrl, clientId, secret, redirectUri } } = require('../../config');

function TypeformToken(code) {

  // r2 still missing formData api :(
  return new Promise((resolve, reject) =>{
   const options = {
     url: `${typeformUrl}/oauth/token`,
     form: {
        grant_type: 'authorization_code',
        code: code,
        client_id: clientId,
        client_secret: secret,
        redirect_uri: redirectUri,
      }
    }
    request.post(options, (err, _, body) => {
      if (err) reject(err)
      resolve(JSON.parse(body));
    })
  })
}

async function TypeformFormList(token) {
  const headers = {Authorization: `Bearer ${token}`}
  const res = await r2(`${typeformUrl}/forms`, {headers}).response
  return await res.json()
}

async function TypeformForm(token, formId) {
  const headers = {Authorization: `Bearer ${token}`}
  const res = await r2(`${typeformUrl}/forms/${formId}`, {headers}).response
  return await res.text()
}

async function TypeformMessages(token, formId) {
  const headers = {Authorization: `Bearer ${token}`}
  const res = await r2(`${typeformUrl}/forms/${formId}/messages`, {headers}).response
  return await res.text()
}

module.exports = {
  TypeformToken,
  TypeformFormList,
  TypeformForm,
  TypeformMessages
};
