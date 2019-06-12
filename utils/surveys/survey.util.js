'use strict';

const { Survey } = require('../../queries');
const joi = require('joi');

function validate(reqData) {
  const formSchema = joi
    .object({
      formid: joi
        .string()
        .alphanum()
        .required(),
      userid: joi
        .string()
        .email()
        .required(),
      shortcode: joi
        .string()
        .length(3, 'utf8')
        .regex(/^[0-9]+$/)
        .required(),
      title: joi.string().required(),
      form: joi.string().required(),
    })
    .unknown()
    .required();

  const { error } = joi.validate(reqData, formSchema);
  if (error) {
    throw new Error(`Config validation error: ${error.message}`);
  }
}

async function shortcode (userid) {
  const code = Math.floor(Math.random() * 999)
  const included = await Survey.includes({ userid, code })
  return  included ? shortcode() : code.toString();
}

module.exports = {
  shortcode,
  validate,
};
