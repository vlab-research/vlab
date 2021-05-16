'use strict';

const joi = require('joi');
const r2 = require('r2');
const { FORMCENTRAL: { url:formcentral } } = require('../../config');

async function validateTranslation({form, translation_conf}) {
  if (!translation_conf.destination && !translation_conf.self) {
    return
  }

  if (translation_conf.destination && translation_conf.self) {
    throw new Error('cant translation both to a destination and to self!')
  }

  const json = {form: JSON.parse(form), ...translation_conf}
  const res = await r2.post(`${formcentral}/translators`, { json }).response

  if (!res.ok) {
    return res.text()
  } 
}

function validate(reqData) {
  const formSchema = joi
    .object({
      formid: joi
        .string()
        .alphanum()
        .required(),
      userid: joi.string().required(),
      messages: joi.string(),
      shortcode: joi.string().required(),
      title: joi.string().required(),
      form: joi.string().required(),
      survey_name: joi.string().required(),
      metadata: joi.object(),
      translation_conf: joi.object(),
    })
    .unknown()
    .required();

  const { error } = joi.validate(reqData, formSchema);
  if (error) {
    throw new Error(
      `Config validation error: ${error.message}. Data: ${JSON.stringify(
        reqData,
        null,
        2,
      )}`,
    );
  }
}

module.exports = {
  validate,
  validateTranslation,
};
