'use strict';

const request = require('request');
const { TYPEFORM: { typeformUrl, clientId, secret, redirectUri } } = require('../../config');

function TypeformToken(code) {
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

function TypeformFormList(token) {
  return new Promise((resolve, reject) =>{
   const options = {
      url: `${typeformUrl}/forms`,
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
    request.get(options, (err, _, body) => {
      if (err) reject(err)
      resolve(JSON.parse(body));
    })
  })
}

function TypeformForm(token, formId) {
  return new Promise((resolve, reject) =>{
   const options = {
      url: `${typeformUrl}/forms/${formId}`,
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
    request.get(options, (err, _, body) => {
      if (err) reject(err)
      resolve(body);
    })
  })
}

module.exports = {
  TypeformToken,
  TypeformFormList,
  TypeformForm
};